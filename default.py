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
_addon_path    = xbmc.translatePath(_addon.getAddonInfo("path") )
_images_path   = _addon_path + "/resources/images/"
__language__   = _addon.getLocalizedString
 
sys.path.append(os.path.join(_addon_path, 'resources', 'lib'))
import mechanize

xbmcplugin.setContent(_addon_handler, 'movies')

dtformat = '%Y-%m-%d %H:%M:%S'

###########
# functions
###########

def build_url(query):
    return _addon_url + '?' + urllib.urlencode(query)

def convertdatetime(dt, sourceformat):
    try:
        return datetime.strptime(dt, sourceformat)
    except TypeError:
        return datetime(*(time.strptime(dt, sourceformat)[0:6]))

def prettydate(dt, addtime=True):    
    if addtime:
        return dt.strftime(xbmc.getRegion("datelong") + ", " + xbmc.getRegion("time").replace(":%S", "").replace("%H%H", "%H"))
    else:
        return dt.strftime(xbmc.getRegion("datelong"))

def getseconds(timestr):
    return sum(int(x) * 60 ** i for i,x in enumerate(reversed(timestr.split(":"))))

##############
# main routine
##############

from datetime import datetime

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
args = dict(urlparse.parse_qsl(sys.argv[2][1:]))
mode = args.get('mode', None)

# main menu, show 'mediatypes'
if mode is None:
    # load menu
    response = urllib.urlopen("http://appsdata.laola1.at/data/telekomsport/ios/basketball/2_0_0/config.json").read()
    jsonResult = json.loads(response)

    # TODO: add error handling (if not existent)
    video_pages = [jsonResult['contentPages'][x] for x in jsonResult['content_items']['videos']['contentPages']]
    cms_base = jsonResult['contentDetails']['Base']['cms_base']
    video_url = jsonResult['contentDetails']['videolist']['url'].replace('{{{cms_base}}}', cms_base)
    
    for key, content_item in jsonResult['content_items'].iteritems():
        if 'leagueId' in content_item:
            url = build_url({'mode': 'content_item', 'content_item': json.dumps(content_item), 'video_pages': json.dumps(video_pages), 'video_url': video_url})
            li = xbmcgui.ListItem(content_item['title'], iconImage=_images_path + content_item['title'].lower() +'.png')
            xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li, isFolder=True)
        
    xbmcplugin.endOfDirectory(_addon_handler)

elif mode == 'content_item':
    video_pages = json.loads(args['video_pages'])
    
    for video_page in video_pages:
        url = build_url({'mode': 'video_page', 'video_page': json.dumps(video_page), 'content_item': args['content_item'], 'video_url': args['video_url'], 'page': 1})
        li = xbmcgui.ListItem(video_page['title'], iconImage='DefaultFolder.png')
        xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li, isFolder=True)
    
    xbmcplugin.endOfDirectory(_addon_handler)

elif mode == 'video_page':
    video_page = json.loads(args['video_page'])
    content_item = json.loads(args['content_item'])
    video_url = args['video_url']
    page = args['page']
    
    video_url = video_url.replace('@@@mediatype@@@', video_page['mediatype'])
    video_url = video_url.replace('@@@page@@@', page)
    video_url = video_url.replace('@@@organization@@@', content_item['leagueId'])
    video_url = video_url.replace('@@@category@@@', video_page.get('category', ""))
    
    response = urllib.urlopen(video_url).read()
    jsonResult = json.loads(response)
    
    videoday = None;
    for content in jsonResult['content']:
        scheduled_start = convertdatetime(content['scheduled_start'], dtformat)
        if videoday is None or (video_page['viewModel'] != "live" and scheduled_start.date() < videoday) or (video_page['viewModel'] == "live" and scheduled_start.date() > videoday):
        #if (video_page['viewModel'] != "live" and (videoday is None or scheduled_start.date() < videoday)) or (video_page['viewModel'] == "live" and (videoday is None or scheduled_start.date() > videoday)):
            li = xbmcgui.ListItem("[COLOR yellow]" + prettydate(scheduled_start, False) + "[/COLOR]")
            li.setProperty("IsPlayable", "false")
            xbmcplugin.addDirectoryItem(handle=_addon_handler, url="", listitem=li)
            videoday = scheduled_start.date()
    
        # TODO: get urls from config
        url = build_url({'mode': 'content', 'id': content['id'], 'scheduled_start': content['scheduled_start'], 'isPay': content['isPay'], 'thumbnailImage': 'https://www.telekombasketball.de' + content['teaser_image_small']})
        li = xbmcgui.ListItem(content['title_long'].split('|')[0], iconImage='https://www.telekombasketball.de' + content['teaser_image_small'])
        li.setProperty('fanart_image', 'https://www.telekombasketball.de' + content['teaser_image_big'])
        duration = getseconds(content['duration']) if content['duration'] else 0
        li.setInfo( "video", { "plot": content['round_1'] + ", " + content['round_2'] + "[CR]" + prettydate(scheduled_start), "duration": duration } )
        li.setProperty('IsPlayable', 'true')
        xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li)

    if int(page) < jsonResult['total_pages']:
        args['page'] = str(int(args['page']) + 1)
        url = build_url(args)
        li = xbmcgui.ListItem('mehr ...')
        xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li, isFolder=True)

    if _addon.getSetting('autoview'):
        xbmc.executebuiltin("Container.SetViewMode(%s)" % _addon.getSetting('mediaview'))
        
    xbmcplugin.endOfDirectory(_addon_handler)

# stream selected video
elif mode == 'content':
    scheduled_start = convertdatetime(args['scheduled_start'], dtformat)
    now = datetime.now()

    if now < scheduled_start:
        xbmcgui.Dialog().ok(_addon_name, __language__(31002), "", prettydate(scheduled_start))
    else:
        if args['isPay'] == 'True':
            if not _addon.getSetting('username'):
                xbmcgui.Dialog().ok(_addon_name, __language__(31001))
                _addon.openSettings()
            else:
                browser.open("https://www.telekombasketball.de/service/oauth/login.php?headto=https://www.telekombasketball.de/")
                browser.select_form(name="login")
                browser.form['pw_usr'] = _addon.getSetting('username')
                browser.form['pw_pwd'] = _addon.getSetting('password')
                browser.submit()
        
        browser.open("https://www.telekombasketball.de/videoplayer/player.php?play=" + args['id'])
        response = browser.response().read()
        if 'class="subscription_error"' in response:
            xbmcgui.Dialog().ok(_addon_name, __language__(31003))
            sys.exit(0)
            
        mobileUrl = re.search('mobileUrl: \"(.*?)\"', response).group(1)

        browser.open(mobileUrl)
        response = browser.response().read()
        
        xmlroot = ET.ElementTree(ET.fromstring(response))
        playlisturl = xmlroot.find('token').get('url')
        auth = xmlroot.find('token').get('auth')
        
        listitem = xbmcgui.ListItem(path=playlisturl + "?hdnea=" + auth, thumbnailImage=args['thumbnailImage'])
        xbmcplugin.setResolvedUrl(_addon_handler, True, listitem)
