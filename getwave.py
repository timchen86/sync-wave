"""A simple webapp2 server."""
import re
import webapp2
import urllib2
import datetime
from datetime import timedelta
from google.appengine.ext import db

import sys
sys.path.insert(0, 'libs')
from BeautifulSoup import BeautifulSoup 

import logging
logger = logging.getLogger(__name__)

from globals import url_InfoLabel
from globals import urls_ipa 

class Wave(db.Model):    
    Kind = db.TextProperty(required=False)
    Time = db.DateTimeProperty(required=False)
    Hmax = db.FloatProperty(required=False)
    Hs = db.FloatProperty(required=False)
    H13rd = db.FloatProperty(required=False)
    Direction = db.FloatProperty(required=False)
    Tav = db.FloatProperty(required=False)
    Tz = db.FloatProperty(required=False)
    Tp = db.FloatProperty(required=False)
    Temperature = db.FloatProperty(required=False)

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:25.0) Gecko/20100101 Firefox/25.0"
ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
ACCEPT_LANGUAGE = "en-US,en;q=0.8,zh-TW;q=0.6,zh;q=0.4"

class ModelUpdatePage(webapp2.RequestHandler):
    def post(self):
        x = self.request.get("x")
        y = self.request.get("y")
        model = self.request.get("model")
        date = self.request.get("date")
        region = self.request.get("region")

        url = url_InfoLabel % (x,y,model,date,region)

        logging.info(url)

        request = urllib2.Request(url=url)
        request.add_header('User-Agent',USER_AGENT)
        request.add_header("Accept", ACCEPT)
        request.add_header("Accept-Language", ACCEPT_LANGUAGE)
        response = urllib2.urlopen(request)
        html = response.read()
        html_nohidden = re.sub(r'style=.*(display:none;")', "", html, flags=re.MULTILINE)
        
        logging.info(html_nohidden)
        self.response.headers['Content-Type'] = 'text/html'
        xmlutf8 = '<?xml version="1.0" encoding="UTF-8"?>'
        self.response.write(xmlutf8+html_nohidden)



class ModelPage(webapp2.RequestHandler):

    MAIN_PAGE_HTML = """\
    <!doctype html>
    <html>
      <body>
        <form action="/update_model" method="post">
          <label for="x">x </label> <input type="text" name="x" value="34.7607"><br>
          <label for="y">y </label> <input type="text" name="y" value="32.7556"><br>
          <label for="model">model </label> <input type="text" name="model" value="wam"><br>
          <label for="model date">model date </label> <input type="text" name="date" value="1403230000"><br>
          <label for="region">region </label> <input type="text" name="region" value="fine"><br>
          <input type="submit" value="Submit"></div>
        </form>
      </body>
    </html>
    """   
    def get(self):
        self.response.write(self.MAIN_PAGE_HTML)



class WavePage(webapp2.RequestHandler):

    def get_date(self, soup):
        fonts_date = soup.findAll("font", {"size":"+1"})
        list_date = [x.getText() for x in fonts_date]

        return list_date

    def get_header(self, soup):
        tables = soup.findAll("table")
        tds = tables[0].find("tr").findAll("td")
        header = [ x.getText() for x in tds ] 
        
        return header
    
    def get_wave(self, soup, date, header):
        wave = []
        tables = soup.findAll("table")

        for j in range(0,len(date)):
            trs = tables[j].findAll("tr")
            for tr in trs[1:]: 
                tds = tr.findAll("td")
                #logging.info(tds)
                data = {}
                for i in range(0,len(header)):
                    text = tds[i].getText()
                    if "Time" in header[i]:
                        data[header[i]] = date[j]+" "+text
                    else:
                        data[header[i]] = text

                wave.append(data)
        
        wave_sorted = sorted(wave, key=lambda k: k['TimeGMT']) 

        return wave_sorted
    
    def db_put(self, kind, wave_sorted):
        n = 0
        u = 0
        for ws in wave_sorted:
            w = Wave()
            w.Kind = kind
            # 26 March 2014 06:30
            w.Time = datetime.datetime.strptime(ws["TimeGMT"],"%d %B %Y %H:%M")

            try: 
                w.Hmax= float(ws["Hmaxmeter"])
            except:
                pass
            try: 
                w.Hs = float(ws["Hsmeter"])
            except:
                pass
            try: 
                w.H13rd = float(ws["H1/3meter"])
            except:
                pass
            try: 
                w.Direction = float(ws["Directiondeg"])
            except:
                pass
            try: 
                w.Tav = float(ws["Tavsec"])
            except:
                pass
            try: 
                w.Tz = float(ws["Tzsec"])
            except:
                pass
            try: 
                w.Tp = float(ws["Tpsec"])
            except:
                pass
            try: 
                w.Temperature = float(ws["TemperatureoC"])
            except:
                pass


            q = Wave.all()
            r = q.filter("Time =", w.Time)
            if r.count() > 0:
                #db.delete(r)
                #w.put()
                u += 1
            else:
                w.put()
                n += 1

        return (n, u)

    def get(self):
        for urls in urls_ipa:
            for kind, url in urls.iteritems():
                request = urllib2.Request(url=url)
                request.add_header('User-Agent',"Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:25.0) Gecko/20100101 Firefox/25.0")
                request.add_header("Accept", "text/html")
                request.add_header("Cache-Control", "max-age=0")
                response = urllib2.urlopen(request)

                html = response.read()
                soup = BeautifulSoup(html)

                date = self.get_date(soup)
                header = self.get_header(soup)
                wave = self.get_wave(soup, date, header)

                logging.info(wave)
                logging.info("lenth of wave: %d" % len(wave))
                
                n,u = self.db_put(kind, wave)

                logging.info("%s: %d new records" % (kind, n))
                self.response.headers['Content-Type'] = 'text/html'
                self.response.write("%s: %d new records<br>" % (kind, n))

        return
 
application = webapp2.WSGIApplication([
    ('/wave', WavePage), 
    ('/model', ModelPage),
    ('/update_model', ModelUpdatePage)], debug=True)



