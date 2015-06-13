import webapp2
import jinja2
import os
import time
import hashlib
import hmac
import random
import string
from google.appengine.ext import db
import urllib2
from xml.dom import minidom
import logging
from google.appengine.api import memcache

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def set_secure_cookie(self, name, val):
        cookie_val = make_secure_val(val)
        self.response.headers.add_header('Set-Cookie', '%s=%s; Path=/' % (name, cookie_val))

    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    def login(self, user):
        self.set_secure_cookie('user_id', str(user.key().id()))

    def logout(self):
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

    # It's called by google appengin framework every request.
    # def initialize(self, *a, **kw):
    #     webapp2.RequestHandler.initialize(self, *a, **kw)
    #     uid = self.read_secure_cookie('user_id')
    #     self.user = uid and User.by_id(int(uid))

class MainPage(Handler):
    def get(self):
        items = self.request.get_all("food")
        self.render("shopping_list.html", items = items)

class FizzBuzz(Handler):
    def get(self):
        n = self.request.get("n", "0")
        if n.isdigit() :
            n = int(n)       
        else :
            n = 0

        self.render("fizzbuzz.html", n = n)

IP_URL = "http://api.hostip.info/?ip="
def get_coords(ip):
    url = IP_URL + ip
    content = None
    try:
        content = urllib2.urlopen(url).read()
    except URLError:
        return

    if content :
        #parse the xml and find the coordinate
        lanlat = get_coodes_xml(content)
        if lanlat :
            return db.GeoPt(lanlat[1], lanlat[0])

def get_coodes_xml(xml):
    d = minidom.parseString(xml)
    coords = d.getElementsByTagName("gml:coordinates")
    if coords and coords[0].childNodes[0].nodeValue:
        return coords[0].childNodes[0].nodeValue.split(',')

GMAPS_URL = "http://maps.googleapis.com/maps/api/staticmap?size=380x263&sensor=false&"

#Point = namedtuple('Point', ["lat", "lon"])

def gmaps_img(points):
    markers = []
    
    for p in points:
        markers.append("markers=%s,%s" % (p.lat, p.lon))
        
    return GMAPS_URL + "&".join(markers)

#CACHE = {}
def top_arts(update = False):
    key = 'top'
    arts = memcache.get(key)
    if arts is None or update:
        logging.error("DB QUERY")
        arts = db.GqlQuery("SELECT * FROM Art ORDER BY created DESC LIMIT 10")

        #prevent the running of multiple query
        arts = list(arts)
        memcache.set(key, arts)

    # if key in CACHE:
    #     arts = CACHE[key]
    # else:
    #     logging.error("DB QUERY")
    #     arts = db.GqlQuery("SELECT * FROM Art ORDER BY created DESC LIMIT 10")

    #     #prevent the running of multiple query
    #     arts = list(arts)
    #     CACHE[key] = arts

    return arts
        
class Ascii(Handler):
    def render_front(self, title="", art="", error=""):
        arts = top_arts()

        #find which arts have coords
        points = filter(None, (a.coords for a in arts))

        # points = []
        # for a in points :
        #     if arts.coords :
        #         points.append(a.coords)

        #if we have any arts coords, make an image url
        img_url = None
        if points :
            img_url = gmaps_img(points)

        self.render("front.html", title = title, art = art, error = error, arts = arts, img_url = img_url)

    def get(self):
        self.write(get_coords(self.request.remote_addr))
        #self.write(repr(get_coords("12.215.42.19")))
        #self.write(repr(get_coords(self.request.remote_addr)))
        self.render_front()

    def post(self):
        title = self.request.get("title")
        art = self.request.get("art")

        if title and art:
            a = Art(title=title, art=art)
            #look up the user's coordinates from their ip
            coords = get_coords(self.request.remote_addr)
            #if we have coordinates, add them to the art
            if coords :
                a.coords = coords

            a.put() #store in the database
            #CACHE.clear()
            top_arts(True)

            self.redirect("/ascii")
            #self.write("thanks!")
        else:
            error = "we need both a title and some artwork!"
            self.render_front(title=title, art=art, error=error)

class Art(db.Model):
    title = db.StringProperty(required = True)
    art = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    coords = db.GeoPtProperty()


def blog_key(name = 'default'):
    return db.Key.from_path('blogs', name)

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)
    
class Post(db.Model):
    subject = db.StringProperty(required = True)
    article = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)

    def render(self):
        self._render_text = self.article.replace('\n','<br>')
        return render_str("blog_post.html", post=self)

class Blogfront(Handler):
    def render_front(self):
        #posts = db.GqlQuery("SELECT * FROM Post ORDER BY created DESC")
        posts = Post.all().ancestor(blog_key()).order('-created')
        self.render("blog_front.html", posts=posts)

    def get(self):
        self.render_front()

    def post(self):
        pass

class Blogpost(Handler):
    def render_post(self, error="", subject="", article=""):
        self.render("blog_new.html", error=error, subject=subject, article=article)

    def get(self):
        self.render_post()

    def post(self):
        subject = self.request.get("subject")
        article = self.request.get("article")

        if subject and article :
            data = Post(parent=blog_key(), subject=subject, article=article)
            data.put()

            #self.redirect("/blog")
            #time.sleep(1)
            self.redirect("/blog/%s" % str(data.key().id()))
        else :
            error = "subject and article are both required."
            self.render_post(error, subject, article)

class Blogperma(Handler):
    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)

        if not post:
            self.error(404)
            return 

        self.render("blog_perma.html", post=post)

#Notice, usually not store in the code.
SECRET = "secret"

#helper. Construct hash uging hmac.
def hash_str(s):
    return hmac.new(SECRET, s).hexdigest()

#helper. Returns hash separeted with "|" from target string.
def make_secure_val(s):
    return "%s|%s" % (s, hash_str(s))

#helper. If given hash is valid, returns original string.
def check_secure_val(h):
    val = h.split('|')[0]
    if h == make_secure_val(val):
        return val

#helper. Rerutns a random fixed length string.
def make_salt(length = 5):
    return ''.join(random.choice(string.ascii_letters) for i in range(length))

#Returns the hashed password which stored in the database.
def make_pw_hash(name, pw, salt = None):
    if not salt :
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s,%s' % (h, salt)

#Check if given name and password are valid. This uses hashed password created by make_pw_hash().
def valid_pw(name, pw, h):
    salt = h.split(',')[1]
    if h == make_pw_hash(name, pw, salt) :
        return True


class CookieHandler(Handler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        visits = 0
        #get a number + hash as string
        visits_cookie_val = self.request.cookies.get('visits')
        if visits_cookie_val :
            cookie_val = check_secure_val(visits_cookie_val)
            #returns a number unless falsified
            if cookie_val :
                visits = int(cookie_val)

        visits += 1

        new_cookie_val = make_secure_val(str(visits))

        self.response.headers.add_header('Set-Cookie', 'visits=%s' % new_cookie_val)

        # #make sure visits is an int
        # if visits.isdigit() :
        #     visits = int(visits) + 1
        # else :
        #     visits = 0

        # self.response.headers.add_header('Set-Cookie', 'visits=%s' % visits)


        if visits > 100 :
            self.write("you are the best ever!")
        else :
            self.write("You have visit this site %s times!" % visits)

class Signup(Handler):
    def render_page(self, username="", email="", error_username="", error_password="", error_verify=""):
        self.render('Signup.html', username=username, email=email, 
            error_username=error_username, error_password=error_password, error_verify=error_verify)

    def get(self):
        self.render_page()

    def post(self):
        self.username = self.request.get("username")
        self.password = self.request.get("password")
        self.verify = self.request.get("verify")
        self.email = self.request.get("email")

        if not self.username :
            error_username = "You need to put your username"
            self.render_page(self.username, self.email, error_username=error_username)

        elif not self.password :
            error_password = "You need to put your password"
            self.render_page(self.username, self.email, error_password=error_password)

        elif self.password != self.verify :
            error_verify = "Your password didn't match."
            self.render_page(self.username, self.email, error_verify=error_verify)

        else :
            #self.response.headers.add_header('Set-Cookie', 'username=%s' % str(self.username))
            #self.response.headers.add_header('Set-Cookie', 'userid=%s' % make_secure_val(str(self.username)))
            #self.redirect("/welcome")
            
            # to define in a inherited class
            self.done()

    def done(self, *a, **kw):
        raise NotImplementedError

class SignupOnly(Signup):
    def done(self):
        if self.username:
            self.render("welcome.html", username = self.username)
        else:
            self.redirect("/signup")

class Register(Signup):
    def done(self):
        #make sure the user doesn't already exist
        u = User.by_name(self.username)
        if u :
            error_username = 'Thiat user already exists.'
            self.render_page(error_username=error_username)

        else :
            u = User.register(self.username, self.password, self.email)
            u.put()

            #set the cookie 'user_id' using User object
            self.login(u)
            self.redirect("/welcome")

class Welcome(Handler):
    def get(self):
        uid = self.read_secure_cookie('user_id')
        #get the user object by uid
        user = uid and User.by_id(int(uid))
        if user:
            self.render("welcome.html", username = user.name)
        else:
            self.redirect("/signup")

    # def get(self):
    #     self.response.headers['Content-Type'] = 'text/plain'
    #     username = self.request.cookies.get("username")
    #     userid = self.request.cookies.get("userid")
    #     if check_secure_val(str(userid)) :
    #         self.write("Welcome, %s" % username)
    #     else :
    #         self.redirect("/signup")

class Login(Handler):
    def render_page(self, error=""):
        self.render("Login.html", error=error)

    def get(self):
        self.render_page()

    def post(self):
        username = self.request.get("username")
        password = self.request.get("password")

        u = User.login(username, password)
        if u :
            self.login(u)
            self.redirect("/welcome")
        else :
            error = "Invalid login"
            self.render_page(error=error)

        # if not username :
        #     error = "Put in your username."
        #     self.render_page(username, error)
        #     return
        
        # self.write("Welcome, %s" % username)

class Logout(Handler):
    def get(self):
        self.logout()
        self.redirect("/signup")
        # self.response.headers.add_header("Set-Cookie", "username=%s" % "")
        # self.response.headers.add_header("Set-Cookie", "userid=%s" % "")
        # self.redirect("signup")

# get the parent's key to make sure the consistency on the database.
def users_key(group = 'default'):
    return db.Key.from_path('users', group)

class User(db.Model):
    name = db.StringProperty(required = True)
    pw_hash = db.StringProperty(required = True)
    email = db.StringProperty()

    @classmethod
    def by_id(cls, uid):
        return User.get_by_id(uid, parent = users_key())

    @classmethod
    def by_name(cls, name):
        u = User.all().filter('name =', name).get()
        return u

    #construct the class with hashing password. (not stored in database yet.)
    @classmethod
    def register(cls, name, pw, email = None):
        pw_hash = make_pw_hash(name, pw)
        return User(parent = users_key(),
                    name = name,
                    pw_hash = pw_hash,
                    email = email)

    #check if the user and the password are match. Reffering to the database.
    @classmethod
    def login(cls, name, pw):
        u = cls.by_name(name)
        #search the entity and give input pw and hashed pw
        if u and valid_pw(name, pw, u.pw_hash):
            return u



app = webapp2.WSGIApplication([
    ('/', MainPage), 
    ('/FizzBuzz', FizzBuzz),
    ('/ascii', Ascii),
    ('/blog/?', Blogfront),
    ('/blog/newpost', Blogpost),
    ('/blog/([0-9]+)', Blogperma),
    ('/cookie', CookieHandler),
    ('/signuponly', SignupOnly),    
    ('/signup', Register),
    ('/welcome', Welcome),
    ('/login', Login),
    ('/logout', Logout),
], debug=True)