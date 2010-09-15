#wikipedia movie summary agent
import re

GOOGLE_JSON_URL = 'http://ajax.googleapis.com/ajax/services/search/web?v=1.0&rsz=large&q=%s'   #[might want to look into language/country stuff at some point] param info here: http://code.google.com/apis/ajaxsearch/documentation/reference.html
WIKIPEDIA_JSON_URL = 'http://en.wikipedia.org/w/api.php?action=query&prop=revisions&titles=%s&rvprop=content&format=json'
#BING_JSON_URL   = 'http://api.bing.net/json.aspx?AppId=879000C53DA17EA8DB4CD1B103C00243FD0EFEE8&Version=2.2&Query=%s&Sources=web&Web.Count=8&JsonType=raw'

#001: Vesmírná odysea (film)]] [[da:Rumrejsen år 2001]] [[de:2001: Odyssee im Weltraum]] [[es:2001: A Space Odyssey (película)]] [[eo:2001: A Space Odyssey (filmo)]] [[fa:۲۰۰۱: اودیسه #فضایی (فیلم)]] [[fr:2001, l'Odyssée de l'espace]] [[gl:2001: A Space Odyssey]] [[ko:2001 스페이스 오디세이]] [[hr:2001: Odiseja u svemiru (1968)]] [[io:2001, spac-odiseo]] [[id:2001: A Space Odyssey]] [[is:2001: Geimævintýraferð]] [[it:2001: Odissea nello spazio]] [[he:2001: אודיסיאה בחלל]] [[la:2001: A Space Odyssey]] [[lv:2001: Kosmosa odiseja (filma)]] [[lt:2001 m. kosminė odisėja]] [[hu:2001: Űrodüsszeia]] [[mk:2001: Вселенска одисеја (филм)]] [[nl:2001: A Space Odyssey]] [[ja:2001年宇宙の旅]] [[no:2001: En romodyssé]] [[pa:੨੦੦੧:ਸਪੇਸ ਓਡੇਸੀ]] [[nds:2001: A Space Odyssey]] [[pl:2001: Odyseja kosmiczna (film)]] [[pt:2001: A Space Odyssey]] [[ro:2001: O odisee spațială (film)]] [[qu:2001: A Space Odyssey]] [[ru:Космическая одиссея 2001 года]] [[simple:2001: A Space Odyssey]] [[sk:2001: Vesmírna odysea]] [[sl:2001: Vesoljska odiseja (film)]] [[sr:2001: Одисеја у свемиру]] [[sh:2001: Odiseja u svemiru (1968)]] [[fi:2001: Avaruusseikkailu (elokuva)]] [[sv:2001 - Ett rymdäventyr (film)]] [[th:2001 จอมจักรวาล (ภาพยนตร์)]] [[tr:2001: Bir Uzay Destanı (film)]] [[uk:Космічна одіссея 2001 року (фільм)]] [[zh:2001太空漫遊 (電影)]]


def Start():
  HTTP.CacheTime = CACHE_1WEEK
  
class WikipediaAgent(Agent.Movies):
  name = 'Wikipedia'
  languages = [Locale.Language.English]
  primary_provider = False
  contributes_to = ['com.plexapp.agents.imdb']
  
  def search(self, results, media, lang):
    
    normalizedName = String.StripDiacritics(media.primary_metadata.title)
    jsonObj = JSON.ObjectFromURL(GOOGLE_JSON_URL % String.Quote('"' + normalizedName + '" film site:wikipedia.org', usePlus=True))
    if jsonObj['responseData'] != None:
      jsonObj = jsonObj['responseData']['results']
      if len(jsonObj) > 0:
        url = jsonObj[0]['unescapedUrl']
        if url.count('wikipedia.org') > 0:
          url = url.split('/')[-1].replace('&','%26')
          
          imdb_year = media.primary_metadata.year

          jsonOBJ = JSON.ObjectFromURL(WIKIPEDIA_JSON_URL % url)['query']['pages']
          rev = jsonOBJ[jsonOBJ.keys()[0]]['revisions']

          # Check for a redirect link
          if rev[0]['*'].count('#REDIRECT [[') > 0:
            url = rev[0]['*'][rev[0]['*'].find('[[') + 2:rev[0]['*'].find(']]')]
            
          # Check for disambiguation
          elif rev[0]['*'].count("In '''movies''':") > 0 or rev[0]['*'].count('{{disambig}}') > 0:
            page = rev[0]['*'].split("In '''movies''':\n")[-1]
            matches = re.findall('\[\[(.*film.*)\|', page)
            
            closestYear = 999
            bestMatch = ''

            for match in matches:
              m = re.search("([12][0-9]{3}) film", match)
              if m:
                ambig_year = int((m.group(1)))
                if abs(ambig_year - imdb_year) < closestYear:
                  closestYear = abs(ambig_year - imdb_year)
                  url = match.replace(' ','_')

          # Grab page and confirm we have the imdb link there, else reduce the score below the threshold
          jsonOBJ = JSON.ObjectFromURL(WIKIPEDIA_JSON_URL % url)['query']['pages']
          rev = jsonOBJ[jsonOBJ.keys()[0]]['revisions'][0]['*']
          score = 100
          if rev.count(media.primary_metadata.id.replace('tt','')) == 0:
            score = score - 20
            Log('********* NO IMDB ID MATCH, REDUCING SCORE')

          results.Append(MetadataSearchResult(
            id    = url,
            score = score))
        
  def update(self, metadata, media, lang):
    jsonOBJ = JSON.ObjectFromURL(WIKIPEDIA_JSON_URL % metadata.id)['query']['pages']
    rev = jsonOBJ[jsonOBJ.keys()[0]]['revisions']
    page = rev[0]['*'].replace("}}\n\n'''''", "}}\n'''''")
    
    try:
      summary = page.split("\n'''''")[1].split('\n==')[0]
    
      #remove the external links
      while summary.find('({{') > 0:
        removeStart = summary.find('({{')
        removeEnd = summary.find('}})')
        if removeEnd == -1:
          break
        summary = summary[:removeStart] + summary[removeEnd + 3:]    
      while summary.find('{{') > 0:
        removeStart = summary.find('{{')
        removeEnd = summary.find('}}')
        if removeEnd == -1:
          break
        summary = summary[:removeStart] + summary[removeEnd + 2:]
    
      #remove reference tags
      while summary.find('<ref>') > 0:
        removeStart = summary.find('<ref')
        removeEnd = summary.find('</ref>')
        if removeEnd == -1:
          break
        summary = summary[:removeStart] + summary[removeEnd + 6:]
            
      #remove the | stuff
      while summary.find('|') > 0:
        firstBar = summary.find('|')
        removeStart = summary[:firstBar].rfind('[[')
        if removeStart == -1:
          break
        summary = summary[:removeStart] + summary[firstBar+1:]
    
      #remove everything else
      replaceStrs = "'''''","''''","'''","''","[[","]]"
      for r in replaceStrs:
        summary = summary.replace(r,"")
    
      summary = String.StripTags(summary).replace('&nbsp;',' ').replace('  ',' ').strip()
      metadata.summary = summary
      
    except:
      Log('Error parsing summary for ' + metadata.id)
    
    # Get other data.
    page = rev[0]['*']
    
    # Directors.
    directors = self.getValues(page, 'director')
    if len(directors) > 0:
      metadata.directors.clear()
      metadata.directors.add(directors[0])
    
    # Cast.
    starring = self.getValues(page, 'starring')
    if len(starring) > 0:
      metadata.roles.clear()
      for member in starring:
        role = metadata.roles.new()
        role.actor = member
    
    # Distributor.
    distributor = self.getValues(page, 'distributor')
    if len(distributor) > 0:
      metadata.studio = distributor[0]
    
    # Poster.
    image = self.getValues(page, 'image')
    if len(image) > 0:
      path = 'http://en.wikipedia.org/wiki/File:' + image[0]
      #data = HTTP.Request(path)
      #if image[0] not in metadata.posters:
      #  metadata.posters[image[0]] = Proxy.Media(data)
      
    writers = self.getValues(page, 'writer')
    runtime = self.getValues(page, 'runtime')

    # Release date.
    released = self.getValues(page, 'released')
    if len(released) > 0:
      availableAt = None
      date = released[0]
      
      # Clean up.
      if len(released) > 4 and released[0].find('date') != -1:
        date = '-'.join(released[1:4])
        
      date = re.sub('\(.*\)', '', date)
      
      try:
        availableAt = Datetime.ParseDate(date)
      except:
        m = re.search(r'([0-9]{4})\|([0-9]{1,2})\|([0-9]{1,2})', date)
        if m:
          s = '%s-%s-%s' % (m.groups(1)[0], m.groups(1)[1], m.groups(1)[2])
          availableAt = Datetime.ParseDate(s)
        else:
          Log("No match for date: " + date)
        
      parent_metadata = metadata.contribution('com.plexapp.agents.imdb')
      if availableAt and parent_metadata is not None and abs(availableAt.year - parent_metadata.year) <= 1:
        metadata.originally_available_at = availableAt.date()
        metadata.year = availableAt.year
      
  def getValues(self, page, name):
  
    value = None
    regexps = ['[ ]+=[\t ]+(.*?)\n\|', '[ ]+=[\t ]+(.*?)\|\n']
    for r in regexps:
      rx = re.compile(name + r, re.IGNORECASE|re.DOTALL|re.MULTILINE)
      m1 = rx.search(page)
      if m1:
        value = m1.groups()[0]

        if value[0:5].lower() == '{{ubl' or value.find('{{Unbulleted list') == 0:
          value = value.split('|')[1:]
        elif value.find('<br />') != -1:
          value = value.split('<br />')
        elif value.find('<br>') != -1:
          value = value.split('<br>')
        elif value.find('<br \\/>') != -1:
          value = value.split('<br \\/>')
        else:
          value = [value]

        break
    
    ret = []    
    if value is not None:
      nuke = ['[[',']]','}}','{{']
    
      for v in value:
        for n in nuke:
          v = v.replace(n, '')
          if v.find('|') != -1 and v.find('date|') == -1:
            v = v.split('|')[1]
          v = re.sub('<[^>]+>', '', v)
          v = v.strip()
          v = v.strip(',')
      
        if v.find("'''") == -1:
          ret.append(v)
    
    return ret
    
