import json
from urllib.request import urlopen
from urllib.parse import quote
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

searchUrl = 'http://api.plos.org/search?'
journalUrls = {'PLoS Biology' : 'http://www.plosbiology.org',
               'PLoS Genetics' : 'http://www.plosgenetics.org',
               'PLoS Computational Biology' : 'http://www.ploscompbiol.org',
               'PLoS Medicine' : 'http://www.plosmedicine.org',
               'PLoS ONE' : 'http://www.plosone.org',
               'PLoS Neglected Tropical Diseases' : 'http://www.plosntds.org',
               'PLoS Pathogens' : 'http://www.plospathogens.org'}
api_key = '&api_key={UnppqeqPjpZEH7nEqkRd}'

def titleSearch(title="Ten Simple Rules"):
    '''
    args:  title - string note: use double quotes
    '''
    return searchUrl + 'q=title:' + title + api_key

def formatArticleUrl(doi,journal):
    '''
    Format a link to the article page, given it's doi and journal
    '''
    return journalUrls.get(journal) + '/article/info%3Adoi%2F' + doi.replace('/','%2F')


def search(query='*:*'):
    '''
    Basic Solr search functionality.
    This takes in a string or dictionary.  If a string is passed, it is assumed to be basic search terms; 
    and if a dictionary is passed, the arguments are passed to solr.

    Returns a list containing dictionary objects for each article found. 
    '''

    if isinstance(query,str): 
        query = { 'q' : query }
    else:
        if 'q' not in query: query['q'] = '*:*' #make sure we include a 'q' parameter
    query['wt'] = 'json' #make sure the return type is json
    query['fq'] = quote('doc_type:full AND !article_type_facet:"Issue Image"') #search only for articles
    query['api_key'] = 'UnppqeqPjpZEH7nEqkRd' # You need to substitute this key value for your own PLoS API key. If you do not have a PLoS API Key, please register for a key at http://api.plos.org/registration/
    
    url = searchUrl;

    for part in query:
        url += '%s%s=%s' % ('&' if url is not searchUrl else '',part,query[part])
    print('Making request to',url) #TEST
    r = requests.get(url)
    soup=BeautifulSoup(r.text)
    docs = soup.findAll('doc') 
    # generate dictionary { docs ('title' : ,'doi': , 'journal': , 'authors': }}
    mydict = {}
    for i in range(0,len(docs)):
        if docs[i].find('arr',{'name':'author_display'}) == None: continue
        else: 
            mydict.setdefault(i,{})
            mydict[i] = {'title':docs[i].find('str',{'name':'title_display'})[i].string,
                         'doi': docs[i].find('str', {'name' : 'id'}).string,
                         'journal': docs[i].find('str',{'name' :'journal'}).string,
                         'date': docs[i].find('date').string,
                         'second_auth': docs[i].find('arr',{'name':'author_display'}).str.string
                         }
        
        
    return mydict

def authorSearch(author='Michael B Eisen', strict=True, limit=10):
    '''
    Search for articles by the given author.

    author - the name of the author
    strict - whether or not the search should be strict, e.g. if we search for "Michael Eisen" without a strict search,
    we'll find articles with authors named Michael, or Eisen. With a strict search, we look for exactly the text "Michael Eisen"
    limit - the number of articles to display	
    '''
    query = {}
    name = quote(author)
    if strict : name = '"' + name + '"' 
    query['q'] = 'author:' + name
    query['fl'] = 'id,journal,title' #specify the fields we need returned
    query['rows'] = limit
    results = search(query)
    print('Articles by %s:' %(author))
    print('*'*10)
    i=0
    for doc in results:
        print('(%s) %s (%s)' % (i+1,results[doc]['title'],formatArticleUrl(results[doc]['doi'],results[doc]['journal'])))

def authorViews(author='Michael B Eisen'):
    '''
    Find the total number of views of articles by the given author.
    author - the name of the author to look up
    '''
    results = search({'q' : 'author:"' + quote(author) + '"',
                      'rows' : 999999, #SOLR limits to 10 results by default 
                      'fl' : 'counter_total_all' #SOLR field containing all time views
                     })
    views = 0
    for doc in results:
        views += doc.get('counter_total_all')
    print('%s has %s all time views on PLoS!' % (author,views))

def graphPubs(start,end,out='publications.csv',query=None):
    '''
    Generate a csv file with the number of publications on each day in the specified range. 

    start - the start date (inclusive)
    end - the end date (exclusive)	
    (Dates should be passed in YYYY-MM-DD format.)
    out - name of file to which results should be written.
    query - addition query parameters, e.g. query='journal:"PLoS ONE"' would graph PLoS ONE publications

    Note that to specify an specific date to SOLR, you must double-quote it; e.g. q=publication_date:"2009-10-19T20:10:00Z/DAY".
    To specify a range, surround it with square brackets, e.g. q=[* TO NOW].  
    See http://wiki.apache.org/solr/SolrQuerySyntax#Specifying_a_Query_Parser
    and http://lucene.apache.org/solr/api/org/apache/solr/util/DateMathParser.html
    '''
    if isinstance(out,str): out = open(out,'w')
    
    for day in listDays(start,end):
        q = 'publication_date:"%s/DAY"%s' % (day, quote(' AND ' + query if query else ''))
        pubs=len(search({'q' : q, 'rows' : 99999}))
        out.write('%s,%s\n' % (day.partition('T')[0],pubs))	
    out.close()

def pubsOn(day,journal=None):
    '''
    List the articles published on the given day.

    day - the day to list publications for, in YYYY-mm-dd format.
    journal - optional journal name to which publications will be restricted.
    '''
    dayFormatted =  datetime.strptime(day,'%Y-%m-%d').strftime('%Y-%m-%dT%H:%M:%SZ')
    q = 'publication_date:"%s/DAY"%s' %(dayFormatted,quote(' AND journal:"' + journal + '"') if journal else '')
    results = search({ 'q' : q, 'fl' : 'title,journal,id', 'rows' : 9999 })
    if len(results) > 0:
        print('Articles published %son %s:' % ('in ' + journal + ' ' if journal else '',day))
        print('*'*10)
        for article in results:
            print('%s) %s (%s)' % (results.index(article) + 1,article.get('title'),formatArticleUrl(article.get('id'),article.get('journal'))))
    else:
        print('No articles were published %son %s:' % ('in ' + journal + ' ' if journal else '',day))

def listDays(start,end):
    '''
    Helper method to return formatted strings for all the days in the range.
    '''
    start=datetime.strptime(start,'%Y-%m-%d')
    end=datetime.strptime(end,'%Y-%m-%d')
    delta = end - start
    days = []
    for day in range(0,delta.days):
        days.append((start + timedelta(days=day)).strftime('%Y-%m-%dT%H:%M:%SZ'))
    return days