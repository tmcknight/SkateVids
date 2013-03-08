from datetime import datetime
import time
import re

####################################################################################################

PLUGIN_PREFIX = "/video/skatevids"

VIMEO_URL         = 'http://www.vimeo.com/%s'
YOUTUBE_URL = 'http://www.youtube.com/watch?v=%s'
YOUTUBE_VIDEO_FORMATS = ['Standard', 'Medium', 'High', '720p', '1080p']
YOUTUBE_FMT = [34, 18, 35, 22, 37]

NAME          = L('Title')

#Sources
CHANNELS_FILE = 'sources.json'

#Feed Types
YOUTUBE = 'youtube'
VIMEO = 'vimeo'

#Artwork
ART           = 'art-default.jpg'
ICON          = 'icon-default.png'
PLUGIN_ICON_NEXT = 'icon-next.png'
PREFS_ICON    = 'icon-prefs.png'
ICON_RECENT = 'icon-recent.png'
ICON_CHANNELS = 'icon-sources.png'

####################################################################################################

def Start():
    Plugin.AddPrefixHandler(PLUGIN_PREFIX, MainMenu, NAME, ICON, ART)
    Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")
    Plugin.AddViewGroup("List", viewMode="List", mediaType="items")
    MediaContainer.art = R(ART)
    MediaContainer.title1 = NAME
    DirectoryItem.thumb = R(ICON)
    VideoItem.thumb = R(ICON)
    
    HTTP.CacheTime = CACHE_1HOUR
    

#####################################################################################################
    
def MainMenu():
    dir = MediaContainer(viewGroup="List")

    str_sources = Resource.Load(CHANNELS_FILE)

    sources = JSON.ObjectFromString(str_sources, encoding='utf-8')
    source_list = []
    all_vids = []

    for source in sources["mainmenu"]:
        vids = []
        
        for feed in source["feeds"]:
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
        
        source['latest_vid_date'] = vids[0]['subtitle']
        source['vids'] = vids
        source_list.append(source)

    source_list.sort(cmp = lambda x, y: cmp(x.get('title', ''), y.get('title', '')))
    all_vids.sort(cmp = lambda x, y: cmp(y.get('subtitle',''), x.get('subtitle','')))

    # recently added items
    dir.Append(Function(DirectoryItem(VidMenu, title='Recently Added', thumb=R(ICON)), vids=all_vids[0:20], include_source_name_in_summary=True))
    # source menu
    dir.Append(Function(DirectoryItem(SourceMenu, title='Sources', thumb=R(ICON)), source_list = source_list))

    dir.Append(PrefsItem(title='Preferences', thumb=R(PREFS_ICON)))

    return dir


#####################################################################################################

def SourceMenu(sender, source_list=[]):
    dir = MediaContainer(viewGroup='List')
    
    for source in source_list:
        dir.Append(Function(DirectoryItem(VidMenu, title=source['title'], thumb=R(source['icon'])), vids=source['vids']))

    return dir


#####################################################################################################

def VidMenu(sender, vids=[], include_source_name_in_summary=False):
    dir = ObjectContainer(title2=L('Videos'))
    
    #add video items to menu
    for vid in vids:
        video = VideoClipObject(
                      title = vid['title'],
                      summary = vid['summary'],
                      originally_available_at = Datetime.ParseDate(vid['subtitle']),
                      thumb=vid['thumb'],
                      url = vid['url'])

        if include_source_name_in_summary:
            video.summary = vid['source'].upper() + ' - ' + video.summary

        dir.add(video)
        #dir.add(URLService.MetadataObjectForURL(vid['url']))

    return dir


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
