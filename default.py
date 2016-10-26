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

# main menu, showing 'mediatypes'
if mode is None:
    # load menu
    response = urllib.urlopen("https://www.telekombasketball.de/feeds/appfeed.php?type=videolist").read()
    jsonResult = json.loads(response)

    for mediatype in jsonResult['mediatypes']:
        url = build_url({'mode': '1', 'mediatype_id': mediatype['id']})
        li = xbmcgui.ListItem(mediatype['title'].title(), iconImage='DefaultFolder.png')
        xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li, isFolder=True)
        
    xbmcplugin.endOfDirectory(_addon_handler)

# submenu, showing video items
elif mode[0] == '1':
    page = 1

    while True:
        response = urllib.urlopen("https://www.telekombasketball.de/feeds/appfeed.php?type=videolist&mediatype="+args['mediatype_id'][0]+"&page="+str(page)).read()
        jsonResult = json.loads(response)

        for content in jsonResult['content']:
            url = build_url({'mode': '4', 'id': content['id'], 'scheduled_start': content['scheduled_start'], 'isPay': content['isPay'], 'thumbnailImage': 'https://www.telekombasketball.de' + content['teaser_image_small']})
            li = xbmcgui.ListItem(content['title_long'].split('|')[0], iconImage='https://www.telekombasketball.de' + content['teaser_image_small'])
            li.setProperty('fanart_image', 'https://www.telekombasketball.de' + content['teaser_image_big'])
            li.setProperty('IsPlayable', 'true')
            xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li)

        # only load max 10 pages for now
        if page < jsonResult['total_pages'] and page < 10:
            page += 1
        else:
           break

    xbmcplugin.endOfDirectory(_addon_handler)

# stream selected video
elif mode[0] == '4':
    scheduled_start = args['scheduled_start'][0]
    now = datetime.datetime.now()
    format = '%Y-%m-%d %H:%M:%S'
    try:
        start = datetime.datetime.strptime(scheduled_start, format)
    except TypeError:
        start = datetime.datetime(*(time.strptime(scheduled_start, format)[0:6]))

    # 'scheduled_start' reflects beginning of game, stream starts 15 minutes earlier
    start = start - datetime.timedelta(minutes=15)

    if now < start:
        xbmcgui.Dialog().ok(_addon_name, __language__(30004), "", str(start))
    else:
        if args['isPay'][0] == 'True':
            if not _addon.getSetting('username'):
                xbmcgui.Dialog().ok(_addon_name, __language__(30003))
                _addon.openSettings()
            else:
                browser.open("https://www.telekombasketball.de/service/oauth/login.php?headto=https://www.telekomeishockey.de/del")
                browser.select_form(name="login")
                browser.form['pw_usr'] = _addon.getSetting('username')
                browser.form['pw_pwd'] = _addon.getSetting('password')
                browser.submit()
        
        browser.open("https://www.telekombasketball.de/videoplayer/player.php?play=" + args['id'][0])
        response = browser.response().read()
        
        if 'class="subscription_error"' in response:
            xbmcgui.Dialog().ok(_addon_name, __language__(30005))
            sys.exit(0)
            
        mobileUrl = re.search('mobileUrl: \"(.*?)\"', response).group(1)

        browser.open(mobileUrl)
        response = browser.response().read()
        
        xmlroot = ET.ElementTree(ET.fromstring(response))
        playlisturl = xmlroot.find('token').get('url')
        auth = xmlroot.find('token').get('auth')
        
        listitem = xbmcgui.ListItem(path=playlisturl + "?hdnea=" + auth, thumbnailImage=args['thumbnailImage'][0])
        xbmcplugin.setResolvedUrl(_addon_handler, True, listitem)
