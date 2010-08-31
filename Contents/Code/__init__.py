#wikipedia movie summary agent
import re

GOOGLE_JSON_URL = 'http://ajax.googleapis.com/ajax/services/search/web?v=1.0&rsz=large&q=%s'   #[might want to look into language/country stuff at some point] param info here: http://code.google.com/apis/ajaxsearch/documentation/reference.html
WIKIPEDIA_JSON_URL = 'http://en.wikipedia.org/w/api.php?action=query&prop=revisions&titles=%s&rvprop=content&format=json'
#BING_JSON_URL   = 'http://api.bing.net/json.aspx?AppId=879000C53DA17EA8DB4CD1B103C00243FD0EFEE8&Version=2.2&Query=%s&Sources=web&Web.Count=8&JsonType=raw'

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
      page = ''
      if len(jsonObj) > 0:
        url = jsonObj[0]['unescapedUrl']
        if url.count('wikipedia.org') > 0:
          url = url.split('/')[-1].replace('&','%26')
          
          imdb_year = media.primary_metadata.year

          jsonOBJ = JSON.ObjectFromURL(WIKIPEDIA_JSON_URL % url)['query']['pages']
          rev = jsonOBJ[jsonOBJ.keys()[0]]['revisions']
          
          #check for a redirect link
          if rev[0]['*'].count('#REDIRECT [[') > 0:
            url = rev[0]['*'][rev[0]['*'].find('[[') + 2:rev[0]['*'].find(']]')]
            
          #check for disambiguation
          elif rev[0]['*'].count("In '''movies''':") > 0:
            page = rev[0]['*'].split("In '''movies''':\n")[-1]
          elif rev[0]['*'].count("In '''modern culture''':"):
            page = rev[0]['*'].split("In '''modern culture''':\n")[-1]
          if page != '':
            page = page.split("\nIn '''")[0]
            closestYear = 999
            bestMatch = ''
            ambigLines = page.split('\n')
            for l in ambigLines:
              l = l.split(']]')[0].split('|')[0].split('[[')[-1]
              pattern = re.compile("([12][0-9]{3}) [a-z0-9\s]* film", re.IGNORECASE)
              m = pattern.search(l)
              if m:
                ambig_year = int((m.group(1)))
                if abs(ambig_year - imdb_year) < closestYear:
                  closestYear = abs(ambig_year - imdb_year)
                  url = l.replace(' ','_')
            
          #grab page and confirm we have the imdb link there, else reduce the score below the threshold
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
    summary = page.split("}}\n'''''")[1].split('\n==')[0]
    
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
