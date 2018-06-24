import json
from datetime import datetime
import os

from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .libs.justwatch_api import JustWatch
from .models import TelegramUser

import telepot
from telepot.routing import by_command
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton

from babel import Locale
from babel.core import UnknownLocaleError

import pytvmaze
from pytvmaze.exceptions import ShowNotFound

BOT_TOKEN = os.environ.get('BOT_TOKEN')
BOT_USERNAME = 'JustWatchTvBot'
PARAM_ITEM='--item'
DEFAULT_COUNTRY = 'GB'

# Create your views here.

def _help(request, bot, update_message, params, **kwargs):
    first_name = update_message.get('from', {}).get('first_name', '')
    country =  __get_user_country(kwargs.get('user'))
    message = render(request, 'api/help.html', {'first_name': first_name, 'country': country}).getvalue()

    return bot.sendMessage(update_message['chat']['id'], message, parse_mode="HTML")

def _set_country(request, bot, update_message, params, **kwargs):
    if len(params) != 1 or len(params[0]) != 2:
        message = """Please type a 2 letters ISO country code!.
For example:  "/country ES" to set country to Spain or "/country AU" to set Australia

Your current country is {}
        """.format(__get_user_country(kwargs.get('user', None)))
        return bot.sendMessage(update_message['chat']['id'], message)
    country = params[0].upper()
    try:
        Locale.parse('und_{}'.format(country))
    except UnknownLocaleError:
        message = """The country {} doesn't exists.
        
Please try with another.""".format(country)
        return bot.sendMessage(update_message['chat']['id'], message)
    user = kwargs.get('user', None)
    if user:
        user.country = country
        user.save()
        message = """Great {}!
Country changed to {}. 
The next results of your /watch command will display info of this country.""".format(user.first_name, country)
        return bot.sendMessage(update_message['chat']['id'], message)
    else:
        message = "An unexpected error has occurred"
        return bot.sendMessage(update_message['chat']['id'], message)

def _watch(request, bot, update_message, params, **kwargs):
    if len(params) == 0:
        message = "Please type a Show or Movie name!"
        return bot.sendMessage(update_message['chat']['id'], message)

    item_index = __get_item_index(params)
    query = ' '.join(params)
    country = __get_user_country(kwargs.get('user', None))
    api = JustWatch(country=country)
    result = api.search_for_item(query=query)
    if len(result['items']) > item_index:
        list_item = result['items'][item_index]
        item = api.get_title(list_item['id'], content_type=list_item.get('object_type', ''))
        providers = api.get_providers()
        offers = item.get('offers', [])
        for offer_i, offer in enumerate(offers):
            for provider in providers:
                if provider['id'] == offer['provider_id']:
                    item['offers'][offer_i]['provider_clear_name'] = provider['clear_name']
                    break
        directors_limit = 3
        actors_limit = 6
        directors = []
        actors = []
        for credit in item.get('credits'):
            if credit.get('role', '') == 'DIRECTOR' and len(directors) < directors_limit:
                directors.append(credit)
            elif credit.get('role', '') == 'ACTOR' and len(actors) < actors_limit:
                actors.append(credit)
            if len(directors) == directors_limit and len(actors) == actors_limit:
                break

        message = render(request, 'api/watch.html', {'item': item, 'directors': directors, 'actors': actors, 'country': country}).getvalue()
        buttonsTop = []
        buttonsBottom = []
        
        poster_url = item.get("poster", "")
        if poster_url:
            poster_url = poster_url.replace('{profile}', 's592')
            buttonsTop.append(InlineKeyboardButton(text='Poster', callback_data="/send_photo {}".format(api.IMG_URL + poster_url)))
        buttonsTop.append(InlineKeyboardButton(text='Fan Art', url="https://www.deviantart.com/?q="+item.get('title')))
        clips = item.get('clips', [])
        trailer = None
        for clip in clips:
            if clip.get('type', '') == 'trailer' and clip.get('provider', '') == 'youtube' and clip.get('external_id', ''):
                trailer = clip
        if trailer:
            buttonsTop.append(InlineKeyboardButton(text='Trailer', url="https://www.youtube.com/watch?v="+trailer['external_id']))
        buttonsTop.append(InlineKeyboardButton(text='More info', url=api.URL+item.get('full_path', '')))
        
        next_item_index = item_index + 1
        if len(result['items']) > next_item_index:
            buttonsBottom.append(
                InlineKeyboardButton(
                    text='More results', 
                    callback_data="/watch {} {}".format(query, PARAM_ITEM + "=" + str(next_item_index))
                )
            )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[buttonsTop, buttonsBottom])
        response = bot.sendMessage(update_message['chat']['id'], message, parse_mode='HTML', disable_web_page_preview=True, reply_markup=keyboard)
    else:
        message = "{} not found.".format(query)
        response = bot.sendMessage(update_message['chat']['id'], message)
    return response

def _when(request, bot, update_message, params, **kwargs):
    if len(params) == 0:
        message = "Please type a Show TV name!"
        return bot.sendMessage(update_message['chat']['id'], message)
    query = ' '.join(params)
    tvm = pytvmaze.TVMaze()
    try:
        show = tvm.get_show(show_name=query)
        context = {
            'show_name': show.name,
            'show_status': show.status,
            'show_summary': show.summary,
            'has_next_episode': show.next_episode is not None,
        }

        if show.next_episode is not None:
            context['next_episode_name'] = show.next_episode.title
            context['next_episode_runtime'] = show.next_episode.runtime
            context['next_episode_season'] = show.next_episode.season_number
            context['next_episode_number'] = show.next_episode.episode_number
            context['next_episode_airdatetime'] = datetime.strptime(show.next_episode.airdate+" "+show.next_episode.airtime, "%Y-%m-%d %H:%M")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='More info', url=show.url)]])
        message = render(request, 'api/when.html', context).getvalue()
        return bot.sendMessage(update_message['chat']['id'], message, parse_mode="HTML", reply_markup=keyboard)
    except ShowNotFound:
        message = "{} not found.".format(query)
        return bot.sendMessage(update_message['chat']['id'], message)

def _send_photo(request, bot, update_message, params, **kwargs):
    if len(params) < 1:
        message = "Invalid photo request"
        return bot.sendMessage(update_message['chat']['id'], message)
    photo_url = params[0]    
    response = bot.sendPhoto(update_message['chat']['id'], photo_url)
    return response

def _send_video(request, bot, update_message, params, **kwargs):
    if len(params) < 1:
        message = "Invalid video request"
        return bot.sendMessage(update_message['chat']['id'], message)
    video_url = params[0]    
    response = bot.sendVideo(update_message['chat']['id'], video_url)
    return response

def _invalid_command(request, bot, update_message, params, **kwargs):
    message = """
Sorry, I don't understand that command.
Type /help to see a list of commands"""
    return bot.sendMessage(update_message['chat']['id'], message)

def __get_user_country(user):
    if user:
        return user.country
    else:
        return DEFAULT_COUNTRY

def __get_item_index(params):
    item_index = 0
    for param_i, param in enumerate(params):
        if param.startswith(PARAM_ITEM + '='):
            try:
                item_index = int(param.replace(PARAM_ITEM + '=', ''))
            except ValueError:
                item_index = 0
            finally:
                del params[param_i]
                break
    return item_index

@csrf_exempt
@require_POST
def telegram_bot(request, token):
    if token != BOT_TOKEN:
        return JsonResponse({'ok': False, 'message': 'Token {} is not a valid token'.format(token)})
    
    try:
        update = json.loads(request.body.decode('utf-8'))
    except ValueError:
        return HttpResponseBadRequest('Invalid request body')
    
    bot = telepot.Bot(BOT_TOKEN)
    message = None
    update_user_from = None
    command_sent = ''
    if 'message' in update:
        message = update['message']
        command_sent = message.get('text')
        update_user_from = message['from']
    elif 'callback_query' in update:
        message = update['callback_query']['message']
        command_sent = update['callback_query']['data']
        update_user_from = update['callback_query']['from']
    else:
        return JsonResponse({'ok': False, 'message': 'Nothing to do.'})

    if not command_sent:
        return JsonResponse({'ok': False, 'message': 'Nothing to do.'})
        
    get_command = by_command(lambda msg_text: msg_text, pass_args=True)
    command = get_command(command_sent)
    """ 
    Commands:
    -------------------
    start - Start bot
    help - List of commands
    country - Change country. This is used to show the results (Suppliers, synopsis, etc. of the series or movie) of the / watch command based on the country
    watch - Know where you can watch(Netflix, HBO, etc.) a TV Show or Movie and other info like description, poster and cast
    when - Know when the next episode of a TV Show comes out
     """
    av_commands = {
        'start': _help,
        'help': _help,
        'country': _set_country,
        'watch': _watch,
        'when': _when,
        'send_photo': _send_photo,
        'send_video': _send_video,
    }
    user = None
    if isinstance(command[0], str):
        func = av_commands.get(command[0].replace('@'+BOT_USERNAME, '').lower(), _invalid_command)
        if message.get('from', None):
            user, user_created = TelegramUser.objects.get_or_create(
                id=update_user_from['id'],
                defaults={
                    'id': update_user_from['id'],
                    'username': update_user_from.get('username', ''),
                    'first_name': update_user_from.get('first_name', ''),
                    'last_name': update_user_from.get('last_name', ''),
                },
            )
            user.last_command = command_sent
            user.save()
    else:
        return JsonResponse({'ok': False, 'message': 'Nothing to do.'})
    response = func(request, bot, message, command[1][0], user=user)
    return JsonResponse(response)

def query(request):
    justwatch = JustWatch(country='ES')
    return JsonResponse(justwatch.search_for_item(query=request.GET.get('q', '')), safe=False)

def providers(request):
    justwatch = JustWatch(country='ES')    
    return JsonResponse(justwatch.get_providers(), safe=False)

def title(request, id):
    justwatch = JustWatch(country='ES')
    return JsonResponse(justwatch.get_title(title_id=id), safe=False)

def test(request):
    tvm = pytvmaze.TVMaze()
    try:
        show = tvm.get_show(show_name='fsdfjdk')
    except ShowNotFound:
        return JsonResponse({'show': "NOT FOUND"}, safe=False)
    
    next_episode = show.next_episode
    return JsonResponse({'show': next_episode.title}, safe=False)