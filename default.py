# -*- coding: utf-8 -*-
import urllib2,urllib,re,os
from stats import *
import xbmcplugin,xbmcgui,xbmcaddon
import simplejson as json
from hashlib import md5
from time import time
from utils import html2text
import sys
import stream

__baseurl__ = 'http://www.stream.cz/API'
_UserAgent_ = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3'
addon = xbmcaddon.Addon('plugin.video.dmd-czech.stream')
profile = xbmc.translatePath(addon.getAddonInfo('profile'))
__settings__ = xbmcaddon.Addon(id='plugin.video.dmd-czech.stream')
home = xbmc.translatePath(__settings__.getAddonInfo('path')).decode("utf-8")
icon = os.path.join( home, 'icon.png' ) 
nexticon = os.path.join( home, 'nextpage.png' )
fanart = os.path.join( home, 'fanart.jpg' )
scriptname = addon.getAddonInfo('name')
quality_index = int(addon.getSetting('quality'))
quality_settings = ["ask", "240p", "360p", "480p", "720p", "1080p"]

use_login = addon.getSetting('use_login') == 'true'

MODE_LIST_SHOWS = 1
MODE_LIST_SEASON = 2
MODE_LIST_EPISODES = 3
MODE_VIDEOLINK = 10
MODE_RESOLVE_VIDEOLINK = 11
MODE_LIST_NEXT_EPISODES = 12
MODE_LIST_FAVOURITES = 13

def getLS(strid):
    return addon.getLocalizedString(strid)

def notify(msg, timeout = 7000):
    xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%(scriptname, msg.encode('utf-8'), timeout, addon.getAddonInfo('icon')))
    log(msg, xbmc.LOGINFO)

def log(msg, level=xbmc.LOGDEBUG):
    if type(msg).__name__=='unicode':
        msg = msg.encode('utf-8')
    xbmc.log("[%s] %s"%(scriptname,msg.__str__()), level)

def logDbg(msg):
    log(msg,level=xbmc.LOGDEBUG)

def logErr(msg):
    log(msg,level=xbmc.LOGERROR)

def makeImageUrl(rawurl):
    return 'http:'+rawurl.replace('{width}/{height}','360/360')

def listContent():
    addDir(getLS(30006),__baseurl__ + '/timeline/latest',MODE_LIST_EPISODES,icon)
    addDir(getLS(30007),__baseurl__ + '/catalogue',MODE_LIST_SHOWS,icon)
    addDir(getLS(30008),__baseurl__ + '/catalogue?channels=3',MODE_LIST_SHOWS,icon)

    if use_login:
        addDir(getLS(30015), __baseurl__ + '/timeline/favourites',MODE_LIST_FAVOURITES,icon)

def listShows(url):
    data = stream.get_json(url)
    items = []
    favourites = []
    ids = []
    fairy_tales = 'channels' in url

    if type(data[u'_embedded'][u'stream:show']) is dict:
        data[u'_embedded'][u'stream:show'] = [data[u'_embedded'][u'stream:show']]

    for item in data[u'_embedded'][u'stream:show']:
        if u'stream:backward' in item[u'_links']:
            link = __baseurl__+item[u'_links'][u'stream:backward'][u'href']
        else:
            link = __baseurl__+item[u'_links'][u'self'][u'href']

        image = makeImageUrl(item[u'image'])
        name = item[u'name']
        ids.append(item['id'])
        items.append((name, link, image, item['id']))

    if use_login and not fairy_tales:
        favourites = stream.query_favourites(ids)

    for item in items:
        name = item[0]
        if item[3] in favourites:
            name =  name + ' [LIGHT]*[/LIGHT]'

        u=composePluginUrl(item[1], MODE_LIST_SEASON, 'name')
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=item[2])

        liz.setInfo( type="Video", infoLabels={ "Title": name } )
        liz.setProperty( "Fanart_Image", fanart )

        if use_login and not fairy_tales:
            container = composePluginUrl(url, MODE_LIST_SHOWS, 'nane')

            if item[3] in favourites:
                menuitems = [( getLS(30014).encode('utf-8'), 'RunScript(plugin.video.dmd-czech.stream, %s, %s, false)' % (container, item[3]))]
            else:
                menuitems = [( getLS(30013).encode('utf-8'), 'RunScript(plugin.video.dmd-czech.stream, %s, %s, true)' % (container, item[3]))]
            liz.addContextMenuItems(menuitems)

        xbmcplugin.addDirectoryItem(handle=addonHandle,url=u,listitem=liz,isFolder=True)

    if 'next' in data[u'_links'].keys():
        listShows(__baseurl__ + data[u'_links'][u'next'][u'href'])

    xbmcplugin.addSortMethod( handle=addonHandle, sortMethod=xbmcplugin.SORT_METHOD_LABEL)

def listFavourites(url):
    data = stream.authorized_request(url)

    if not u'_embedded' in data:
        return

    if type(data[u'_embedded'][u'stream:episode']) is dict:
        data[u'_embedded'][u'stream:episode'] = [data[u'_embedded'][u'stream:episode']]

    for item in data[u'_embedded'][u'stream:episode']:
        link = __baseurl__ + item[u'_links'][u'self'][u'href']

        image = makeImageUrl(item[u'image'])
        show = item['_embedded']['stream:show']['name']
        name = '[LIGHT]%s[/LIGHT] | %s' % (show, item[u'name'])

        addItem(name, link, MODE_RESOLVE_VIDEOLINK, image, False, islatest=False)

    if 'next' in data[u'_links'].keys():
        addDir(u'[B][COLOR blue]'+getLS(30004)+u' >>[/COLOR][/B]', __baseurl__ + data[u'_links']['next']['href'], MODE_LIST_FAVOURITES, nexticon)

def listSeasons(url):
    data = stream.get_json(url)
    seasons = data[u'_embedded'][u'stream:season']
    if type(seasons) is dict:
        listSeasonEpisodes(seasons)
    elif type(seasons) is list:
        for season in seasons:
            link = __baseurl__+season[u'_links'][u'self'][u'href']
            name = u'[B][COLOR blue]' + season[u'name'] + u' >>[/COLOR][/B]'
            addDir(name,link,MODE_LIST_EPISODES,nexticon)
        for season in seasons:
            listSeasonEpisodes(season, season[u'name'])
    if (u'_links' in data) and (u'next' in data[u'_links']):
        link = __baseurl__+data[u'_links'][u'next'][u'href']
        addDir(u'[B][COLOR blue]'+getLS(30004)+u' >>[/COLOR][/B]',link,MODE_LIST_SEASON,nexticon)

def addEpisode(item, season_name='', islatest=False):
    link = __baseurl__+item[u'_links'][u'self'][u'href']
    image = makeImageUrl(item[u'image'])
    name = item[u'name']
    if u'order' in item:
        name = str(item[u'order']) +'. '+ name
    if (len(season_name)==0) and ((u'_embedded' in item) and (u'stream:show' in item[u'_embedded'])) :
        season_name = item[u'_embedded'][u'stream:show'][u'name']
    if len(season_name):
        name = season_name + ' | ' + name
    if quality_index == 0:
        addDir(name,link,MODE_VIDEOLINK,image)
    else:
        addUnresolvedLink(name,link,image,islatest)

def listSeasonEpisodes(data, season_name='', islatest=False):
    if (u'_embedded' in data) and (u'stream:episode' in data[u'_embedded']):
        episodes=data[u'_embedded'][u'stream:episode']
        if type(episodes) is dict:
            addEpisode(episodes, season_name, islatest)
        elif type(episodes) is list:
            for item in episodes:
                addEpisode(item, season_name, islatest)
    if (u'_links' in data) and (u'next' in data[u'_links']):
        link = __baseurl__+data[u'_links'][u'next'][u'href']
        addDir(u'[B][COLOR blue]'+getLS(30004)+u' >>[/COLOR][/B]',link,MODE_LIST_EPISODES,nexticon)

def listEpisodes(url):
    data = stream.get_json(url)
    islatest='/timeline/latest' in url
    listSeasonEpisodes(data, '', islatest)
    
def listNextEpisodes(url):
    data = stream.get_json(url)
    try:
        link = __baseurl__+data[u'_embedded'][u'stream:show'][u'_links'][u'self'][u'href']
        listSeasons(link)
    except:
        logDbg('Další epizody nenalezeny')

def videoLink(url,name):
    data = stream.get_json(url)
    name = data[u'name']
    thumb = makeImageUrl(data[u'image'])
    popis = html2text(data[u'detail'])
    logDbg(url)
    for item in data[u'video_qualities']:
        try:
            for fmt in item[u'formats']:
                if fmt[u'type'] == 'video/mp4':
                    stream_url = fmt[u'source']
                    quality = fmt[u'quality']
                    addLink(quality+' '+name,stream_url,thumb,popis)
        except:
            continue
    try:
        link = __baseurl__+data[u'_embedded'][u'stream:show'][u'_links'][u'self'][u'href']
        image = makeImageUrl(data[u'_embedded'][u'stream:show'][u'image'])
        name = data[u'_embedded'][u'stream:show'][u'name']
        addDir(u'[B][COLOR blue]'+getLS(30004)+u' >>[/COLOR][/B]',link,MODE_LIST_SEASON,image)
    except:
        logDbg('Další epizody nenalezeny')

def resolveVideoLink(url,name):
    data = stream.get_json(url)
    name = data[u'name']
    thumb = makeImageUrl(data[u'image'])
    popis = html2text(data[u'detail'])
    qa = []
    logDbg("Resolving video URL for quality " + quality_settings[quality_index] + " from: " + url)
    for item in data[u'video_qualities']:
        try:
            for fmt in item[u'formats']:
                if fmt[u'type'] == 'video/mp4':
                    stream_url = fmt[u'source']
                    quality = fmt[u'quality']
                    qa.append((quality, stream_url))
        except:
            continue
    if len(qa) == 0:
        # no video available...
        notify(getLS(30003))
        xbmcplugin.setResolvedUrl(handle=addonHandle, succeeded=False, listitem=xbmcgui.ListItem(label="video", path=""))
        return
    # sort available qualities according desired one
    quality_sorted = quality_settings[quality_index:0:-1]
    quality_sorted += quality_settings[quality_index+1:]
    
    stream_url = ""
    for qf in quality_sorted:
        match_quality = [q for q in qa if q[0] == qf]
        if len(match_quality):
            stream_url = match_quality[0][1]
            break
    
    if stream_url == "":
        logErr("No video stream found!")
        xbmcplugin.setResolvedUrl(handle=addonHandle, succeeded=False, listitem=xbmcgui.ListItem(label="video", path=""))
        return

    logDbg("Resolved URL: "+stream_url)
    if match_quality[0][0] != quality_settings[quality_index]:
        notify(getLS(30002) % (quality_settings[quality_index], match_quality[0][0]))
    
    liz = xbmcgui.ListItem(path=stream_url, iconImage="DefaultVideo.png")
    liz.setInfo( type="Video", infoLabels={ "Title": name, "Plot": popis} )
    liz.setProperty('IsPlayable', 'true')
    liz.setProperty( "icon", thumb )
    xbmcplugin.setResolvedUrl(handle=addonHandle, succeeded=True, listitem=liz)

def getParams():
    param=[]
    paramstring=sys.argv[2]
    if len(paramstring)>=2:
        params=sys.argv[2]
        cleanedparams=params.replace('?','')
        if (params[len(params)-1]=='/'):
            params=params[0:len(params)-2]
        pairsofparams=cleanedparams.split('&')
        param={}
        for i in range(len(pairsofparams)):
            splitparams={}
            splitparams=pairsofparams[i].split('=')
            if (len(splitparams))==2:
                param[splitparams[0]]=splitparams[1]
    return param

def addLink(name,url,iconimage,popis):
    logDbg("addLink(): '"+name+"' url='"+url+ "' img='"+iconimage+"' popis='"+popis+"'")
    ok=True
    liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels={ "Title": name, "Plot": popis} )
    liz.setProperty( "Fanart_Image", fanart )
    ok=xbmcplugin.addDirectoryItem(handle=addonHandle,url=url,listitem=liz)
    return ok

def composePluginUrl(url, mode, name):
    return sys.argv[0]+"?url="+urllib.quote_plus(url.encode('utf-8'))+"&mode="+str(mode)+"&name="+urllib.quote_plus(name.encode('utf-8'))

def addItem(name,url,mode,iconimage,isfolder,islatest=False):
    u=composePluginUrl(url,mode,name)
    ok=True
    liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels={ "Title": name } )
    liz.setProperty( "Fanart_Image", fanart )
    if not isfolder:
        liz.setProperty("IsPlayable", "true")
        menuitems = []
        if islatest:
            next_url = composePluginUrl(url,MODE_LIST_NEXT_EPISODES,name)
            menuitems.append(( getLS(30004).encode('utf-8'), 'XBMC.Container.Update('+next_url+')' ))
        if quality_index != 0:
            select_quality_url = composePluginUrl(url,MODE_VIDEOLINK,name)
            menuitems.append(( getLS(30005).encode('utf-8'), 'XBMC.Container.Update('+select_quality_url+')' ))
        liz.addContextMenuItems(menuitems)
    ok=xbmcplugin.addDirectoryItem(handle=addonHandle,url=u,listitem=liz,isFolder=isfolder)
    return ok

def addDir(name,url,mode,iconimage):
    logDbg("addDir(): '"+name+"' url='"+url+"' icon='"+iconimage+"' mode='"+str(mode)+"'")
    return addItem(name,url,mode,iconimage,True)

def addUnresolvedLink(name,url,iconimage,islatest=False):
    mode=MODE_RESOLVE_VIDEOLINK
    logDbg("addUnresolvedLink(): '"+name+"' url='"+url+"' icon='"+iconimage+"' mode='"+str(mode)+"'")
    return addItem(name,url,mode,iconimage,False,islatest)

addonHandle=int(sys.argv[1])
params=getParams()
url=None
name=None
thumb=None
mode=None

try:
    url=urllib.unquote_plus(params["url"])
except:
    pass
try:
    name=urllib.unquote_plus(params["name"])
except:
    pass
try:
    mode=int(params["mode"])
except:
    pass

logDbg("Mode: "+str(mode))
logDbg("URL: "+str(url))
logDbg("Name: "+str(name))

try:
    if mode==None or url==None or len(url)<1:
        STATS("OBSAH", "Function")
        listContent()

    elif mode==MODE_LIST_SHOWS:
        STATS("LIST_SHOWS", "Function")
        listShows(url)

    elif mode==MODE_LIST_SEASON:
        STATS("LIST_SEASON", "Function")
        listSeasons(url)

    elif mode==MODE_LIST_EPISODES:
        STATS("LIST_EPISODES", "Function")
        listEpisodes(url)

    elif mode==MODE_VIDEOLINK:
        STATS(name, "Item")
        videoLink(url,name)

    elif mode==MODE_RESOLVE_VIDEOLINK:
        resolveVideoLink(url,name)
        STATS(name, "Item")
        sys.exit(0)

    elif mode==MODE_LIST_NEXT_EPISODES:
        STATS("LIST_NEXT_EPISODES", "Function")
        listNextEpisodes(url)

    elif mode==MODE_LIST_FAVOURITES:
        STATS("LIST_FAVOURITES", "Function")
        listFavourites(url)

except stream.InvalidCredentials as e:
    open_settings = xbmcgui.Dialog().yesno(addon.getAddonInfo('name'), getLS(30016), getLS(30017))

    if open_settings:
        addon.openSettings()


xbmcplugin.endOfDirectory(addonHandle)
