# Copyright (C) 2014 hubsif (hubsif@gmx.de)
#
# This program is free software; you can redistribute it and/or modify it under the terms 
# of the GNU General Public License as published by the Free Software Foundation; 
# either version 2 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; 
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. 
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; 
# if not, see <http://www.gnu.org/licenses/>.

##############
# preparations
##############

import xbmc, xbmcplugin, xbmcgui, xbmcaddon
import os, sys, re, json, string, random, time
import xml.etree.ElementTree as ET
import urllib
import urlparse

_addon_id      = 'plugin.video.tk_bbl'
_addon         = xbmcaddon.Addon(id=_addon_id)
_addon_name    = _addon.getAddonInfo('name')
_addon_handler = int(sys.argv[1])
_addon_url     = sys.argv[0]
_addon_path    = _addon.getAddonInfo('path').decode(sys.getfilesystemencoding())
__language__   = _addon.getLocalizedString
 
sys.path.append(os.path.join(_addon_path, 'resources', 'lib'))
import mechanize

# don't know if that's needed, as it is already defined in addon.xml
xbmcplugin.setContent(_addon_handler, 'videos')


###########
# functions
###########

def build_url(query):
    return _addon_url + '?' + urllib.urlencode(query)


##############
# main routine
##############

import datetime
datetime.datetime.now()
datetime.datetime.utcnow()

browser = mechanize.Browser()
browser.set_handle_robots(False)

# urllib ssl fix
import ssl
from functools import wraps
def sslwrap(func):
    @wraps(func)
    def bar(*args, **kw):
        kw['ssl_version'] = ssl.PROTOCOL_TLSv1
        return func(*args, **kw)
    return bar
ssl.wrap_socket = sslwrap(ssl.wrap_socket)

# get arguments
args = urlparse.parse_qs(sys.argv[2][1:])
mode = args.get('mode', None)

if mode is None:
    # load live games
    browser.open("https://www.telekombasketball.de/feed/getTeaser.php")
    response = browser.response().read()
    xmlroot = ET.ElementTree(ET.fromstring(response))
    
    for video in xmlroot.getiterator('VIDEO'):
        if video.get('ISLIVESTREAM') == 'true' and video.get('ISLIVE') == 'true':
            url = build_url({'mode': '3', 'id': video.get('ID'), 'scheduled_start': video.get('scheduled_start')})
            li = xbmcgui.ListItem(video.find('TITLE').text, iconImage=video.find('GAME_IMG').text, thumbnailImage=video.find('GAME_IMG').text)
            li.setProperty('fanart_image', video.find('IMAGE_ORIGINAL').text)
            li.setProperty('IsPlayable', 'true')
            xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li)

    # load menu
    browser.open("https://www.telekombasketball.de/feed/getFilter.php")
    response = browser.response().read()
    jsonResult = json.loads(response)
    
    for rounds in jsonResult['children']:
        url = build_url({'mode': '1', 'text': rounds['text']})
        li = xbmcgui.ListItem(rounds['text'], iconImage='DefaultFolder.png')
        xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li, isFolder=True)

    # load specials        
    url = build_url({'mode': '2', 'featured': True})
    li = xbmcgui.ListItem("Featured", iconImage='DefaultFolder.png')
    xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li, isFolder=True) 

    xbmcplugin.endOfDirectory(_addon_handler)

elif mode[0] == '1':
    browser.open("https://www.telekombasketball.de/feed/getFilter.php")
    response = browser.response().read()
    jsonResult = json.loads(response)
    
    round = args['text'][0]
    
    for rounds in jsonResult['children']:
        if rounds['text'] == round:
            for games in rounds['children']:
                url = build_url({'mode': '2', 'href': games['href']})
                li = xbmcgui.ListItem(games['text'], iconImage='DefaultFolder.png')
                xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li, isFolder=True)
    xbmcplugin.endOfDirectory(_addon_handler)

elif mode[0] == '2':
    if args.has_key('featured'):
        browser.open("https://www.telekombasketball.de/feed/getFeatured.php")
    else:
        browser.open("https://www.telekombasketball.de/feed/app_video.feed.php?targetID=8,20&" + args['href'][0])
    response = browser.response().read()
    xmlroot = ET.ElementTree(ET.fromstring(response))
        
    for video in xmlroot.getiterator('VIDEO'):
        url = build_url({'mode': '3', 'id': video.get('ID'), 'scheduled_start': video.get('scheduled_start')})
        li = xbmcgui.ListItem(video.find('TITLE').text, iconImage=video.find('GAME_IMG').text, thumbnailImage=video.find('GAME_IMG').text)
        li.setProperty('fanart_image', video.find('IMAGE_ORIGINAL').text)
        li.setProperty('IsPlayable', 'true')
        xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li)

    xbmcplugin.endOfDirectory(_addon_handler)

elif mode[0] == '3':
    if not _addon.getSetting('username'):
        xbmcgui.Dialog().ok(_addon_name, __language__(30003))
        _addon.openSettings()
    else:
        scheduled_start = args['scheduled_start'][0]
        now = datetime.datetime.now()
        format = '%Y-%m-%d %H:%M:%S'
        try:
            start = datetime.datetime.strptime(scheduled_start, format)
        except TypeError:
            start = datetime.datetime(*(time.strptime(scheduled_start, format)[0:6]))
            
        print xbmc.getRegion('time')
        
        if now < start:
            xbmcgui.Dialog().ok(_addon_name, __language__(30004), "", args['scheduled_start'][0])
        else:
            rand = random.randrange(1000000000,9999999999)
            time = int(time.time())
            state = str(time) + str(rand);

            browser.open("https://www.telekombasketball.de")
            browser.open("https://accounts.login.idm.telekom.com/oauth2/auth?response_type=code&client_id=10LIVESAM30000004901BEKOBBL0000000000000&scope=openid&redirect_uri=http:%2F%2Fwww.telekombasketball.de%2Foauth.php%3Frequest%3Dlogin%26headto%3Dhttp:%2F%2Fwww.telekombasketball.de%2F&state="+state+"&claims=%7B%22id_token%22%3A%7B%22urn%3Atelekom.com%3Aall%22%3Anull%7D%7D")

            browser.select_form(name="login")
            browser.form['pw_usr'] = _addon.getSetting('username')
            browser.form['pw_pwd'] = _addon.getSetting('password')
            browser.submit()

            browser.open("https://www.telekombasketball.de/videoplayer/player.php?play=" + args['id'][0])
            response = browser.response().read()
            
            mobileUrl = re.search('mobileUrl: \"(.*?)\"', response).group(1)
            
            browser.open(mobileUrl)
            response = browser.response().read()
            xmlroot = ET.ElementTree(ET.fromstring(response))
            playlisturl = xmlroot.find('token').get('url')
            auth = xmlroot.find('token').get('auth')
            
            listitem = xbmcgui.ListItem(path=playlisturl + "?hdnea=" + auth)
            xbmcplugin.setResolvedUrl(_addon_handler, True, listitem)
