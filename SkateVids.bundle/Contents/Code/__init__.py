from datetime import datetime
import time
import re

####################################################################################################

PLUGIN_PREFIX = "/video/skatevids"

VIMEO_URL = 'http://www.vimeo.com/%s'
YOUTUBE_URL = 'http://www.youtube.com/watch?v=%s'
YOUTUBE_VIDEO_FORMATS = ['Standard', 'Medium', 'High', '720p', '1080p']
YOUTUBE_FMT = [34, 18, 35, 22, 37]

NAME = L('Title')

#Sources
CHANNELS_FILE = 'sources.json'

#Feed Types
YOUTUBE = 'youtube'
VIMEO = 'vimeo'

#Artwork
ART = 'art-default.jpg'
ICON = 'icon-default.png'
PLUGIN_ICON_NEXT = 'icon-next.png'
PREFS_ICON = 'icon-prefs.png'
ICON_RECENT = 'icon-recent.png'
ICON_CHANNELS = 'icon-sources.png'

####################################################################################################

def Start():
    # Plugin.AddPrefixHandler(PLUGIN_PREFIX, MainMenu, NAME, ICON, ART)
    # Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")
    # Plugin.AddViewGroup("List", viewMode="List", mediaType="items")
    # MediaContainer.art = R(ART)
    # MediaContainer.title1 = NAME
    # DirectoryItem.thumb = R(ICON)
    # VideoItem.thumb = R(ICON)
    ObjectContainer.title1 = NAME
    HTTP.CacheTime = CACHE_1HOUR
    

#####################################################################################################
@handler('/video/skatevids', NAME)
def MainMenu():
    oc = ObjectContainer()

    Log('add recently added menu item')
    # recently added items
    oc.add(DirectoryObject(
        key = Callback(VidMenu, limit=40, include_source_name_in_summary = True),
        title = 'Recently Added',
        thumb = R(ICON)
    ))

    # oc.Append(Function(DirectoryItem(VidMenu, title='Recently Added', thumb=R(ICON)), vids=all_vids[0:20], include_source_name_in_summary=True))
    
    # source menu

    Log('add sources menu item')
    oc.add(DirectoryObject(
        key = Callback(SourceMenu),
        title = 'Sources',
        thumb = R(ICON)
    ))

    # oc.Append(Function(DirectoryItem(SourceMenu, title='Sources', thumb=R(ICON)), source_list = source_list))

    #oc.add(PrefsItem(title='Preferences', thumb=R(PREFS_ICON)))

    return oc


#####################################################################################################
def SourceMenu():
    oc = ObjectContainer()
    str_sources = Resource.Load(CHANNELS_FILE)

    sources = JSON.ObjectFromString(str_sources, encoding='utf-8')
    sources['mainmenu'].sort(cmp = lambda x, y: cmp(x.get('title', ''), y.get('title', '')))
    for source in sources['mainmenu']: 
        oc.add(DirectoryObject(
            key = Callback(VidMenu, source=source['title']),
            title = source['title'],
            thumb = R(source['icon'])
        ))
        # oc.Append(Function(DirectoryItem(VidMenu, title=source['title'], thumb=R(source['icon'])), vids=source['vids']))

    return oc


#####################################################################################################

def VidMenu(source = "", limit = 100, include_source_name_in_summary=False):
    oc = ObjectContainer(title2=L('Videos'))

    vids = LoadVideos(source_name = source, limit = limit)
    
    #add video items to menu
    for vid in vids:
        summary = vid['summary']
        if include_source_name_in_summary:
            summary = vid['source'].upper() + ' - ' + vid['summary']

        video = VideoClipObject(
                      title = vid['title'],
                      summary = summary,
                      originally_available_at = Datetime.ParseDate(vid['subtitle']),
                      thumb=vid['thumb'],
                      url = vid['url'])

        oc.add(video)
        # dir.add(URLService.MetadataObjectForURL(vid['url']))

    return oc
#################

def LoadVideos(source_name = "", limit = 100):
    str_sources = Resource.Load(CHANNELS_FILE)
    sources = JSON.ObjectFromString(str_sources, encoding='utf-8')
    source_list = []
    all_vids = []
    Log('loading sources')
    for source in sources["mainmenu"]:
        if source_name != "" and source_name != source['title']:
            continue

        vids = []
        
        for feed in source["feeds"]:
            Log('loading ' + feed['url'])
            type = feed['type']
            url = feed['url']

            if type == VIMEO:
                items = VimeoFeedItems(feed=url)
            elif type == YOUTUBE:
                items = YouTubeFeedItems(feed=url)

            for vid in items:
                vid['source'] = source['title']

            vids.extend(items)
            all_vids.extend(items)
        
        vids.sort(cmp = lambda x, y: cmp(y.get('subtitle',''), x.get('subtitle','')))
        
        if len(vids):
            source['latest_vid_date'] = vids[0]['subtitle']
        source['vids'] = vids
        source_list.append(source)

    all_vids.sort(cmp = lambda x, y: cmp(y.get('subtitle',''), x.get('subtitle','')))
    Log('done loading sources')

    if len(all_vids) < limit:
        limit = len(all_vids)

    return all_vids[0:limit]

#####################################################################################################

def YouTubeFeedItems(feed='', start_index=1):
    items = []

    if '?' in feed:
        the_feed = feed + '&start-index=' + str(start_index)
    else:
        the_feed = feed + '?start-index=' + str(start_index)

    rawfeed = JSON.ObjectFromURL(the_feed, encoding='utf-8',cacheTime=CACHE_1HOUR)
    
    if rawfeed['feed'].has_key('entry'):
      for video in rawfeed['feed']['entry']:
        if video.has_key('yt$videoid'):
          video_id = video['yt$videoid']['$t']
        elif video['media$group'].has_key('media$player'):
          try:
            video_page = video['media$group']['media$player'][0]['url']
          except:
            video_page = video['media$group']['media$player']['url']
          video_id = re.search('v=([^&]+)', video_page).group(1)
        else:
          video_id = None      
        title = video['title']['$t']

        if (video_id != None) and not(video.has_key('app$control')):
            try:
                published = Datetime.ParseDate(video['published']['$t']).strftime('%Y-%m-%d')
            except: 
                published = Datetime.ParseDate(video['updated']['$t']).strftime('%Y-%m-%d')
            if video.has_key('content') and video['content'].has_key('$t'):
                summary = video['content']['$t']
            else:
                summary = video['media$group']['media$description']['$t']
            duration = int(video['media$group']['yt$duration']['seconds']) * 1000
            try:
                rating = float(video['gd$rating']['average']) * 2
            except:
                rating = 0
            thumb = video['media$group']['media$thumbnail'][1]['url']
            
            items.append({
                'type': YOUTUBE,
                'id': video_id,
                'url': YOUTUBE_URL % video_id,
                'title': title,
                'summary': summary,
                'duration': duration,
                'thumb': thumb,
                'subtitle': published
            })

    return items


#####################################################################################################

def VimeoFeedItems(feed='', page=1):

    items = []

    counter = 0
    
    if '?' in feed:
        the_feed = feed + '&page=' + str(page)
    else:
        the_feed = feed + '?page=' + str(page)

    rawfeed = JSON.ObjectFromURL(the_feed, encoding='utf-8',cacheTime=CACHE_1HOUR)

    for video in rawfeed:
        counter = counter + 1
        video_id = video['id']
        title = video['title']
        published = Datetime.ParseDate(video['upload_date']).strftime('%Y-%m-%d')
        summary = video['description']
        thumb = video['thumbnail_large']
        duration = int(video['duration']) * 1000

        items.append({
            'type': VIMEO,
            'id': video_id,
            'url': VIMEO_URL % video_id,
            'title': title,
            'summary': summary,
            'duration': duration,
            'thumb': thumb,
            'subtitle': published
        })
        
    return items


#####################################################################################################

def Thumb(url):
  try:
    data = HTTP.Request(url, cacheTime=CACHE_1WEEK).content
    return DataObject(data, 'image/jpeg')
  except:
    return Redirect(R(ICON))


#####################################################################################################