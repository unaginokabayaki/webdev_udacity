import webapp2
import jinja2
import os
import time

from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

form_html = """
<form>
<h2>Add food</h2>
<input type="text" name="food">
%s
<button>Add</button>
</form>
"""

hidden_html = """
<input type="hidden" name="food" value="%s">
"""

item_html = "<li>%s</li>"


shopping_list_html = """
<br>
<br>
<h2>Shopping List</h2>
<ul>
%s
</ul>
"""


class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

class MainPage(Handler):
    def get(self):
        items = self.request.get_all("food")
        self.render("shopping_list.html", items = items)


        # output = form_html
        # output_hidden = ""

        # items = self.request.get_all("food")
        # if items:
        #     output_items = ""
        #     for item in items:
        #         output_hidden += hidden_html % item
        #         output_items += item_html % item

        #     output_shopping = shopping_list_html % output_items
        #     output += output_shopping

        # output = output % output_hidden

        # self.write(output)

class FizzBuzz(Handler):
    def get(self):
        n = self.request.get("n", "0")
        if n.isdigit() :
            n = int(n)       
        else :
            n = 0

        self.render("fizzbuzz.html", n = n)

class Ascii(Handler):
    def render_front(self, title="", art="", error=""):
        arts = db.GqlQuery("SELECT * FROM Art ORDER BY created DESC")

        self.render("front.html", title = title, art = art, error = error, arts = arts)

    def get(self):
        self.render_front()

    def post(self):
        title = self.request.get("title")
        art = self.request.get("art")

        if title and art:
            a = Art(title=title, art=art)
            a.put() #store in the database

            self.redirect("/Ascii")
            #self.write("thanks!")
        else:
            error = "we need both a title and some artwork!"
            self.render_front(title=title, art=art, error=error)

class Art(db.Model):
    title = db.StringProperty(required = True)
    art = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)

def blog_key(name = 'default'):
    return db.key.from_path('blogs', name)

class Post(db.Model):
    subject = db.StringProperty(required = True)
    article = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)

    def render(self):
        self._render_text = self.content.replace('/n','<br>')
        return render_str("blog_post.html", p=self)

class Blogfront(Handler):
    def render_front(self):
        posts = db.GqlQuery("SELECT * FROM Post ORDER BY created DESC")
        #posts = Post.all().order('-created')
        self.render("blog_front.html", posts=posts)

    def get(self):
        self.render_front()

    def post(self):
        pass

class Blogpost(Handler):
    def render_post(self, error="", subject="", article=""):
        self.render("blog_post.html", error=error, subject=subject, article=article)

    def get(self):
        self.render_post()

    def post(self):
        subject = self.request.get("subject")
        article = self.request.get("article")

        if subject and article :
            data = Post(subject=subject, article=article)
            data.put()

            time.sleep(1)
            self.redirect("/blog")
        else :
            error = "subject and article are both required."
            self.render_post(error, subject, article)


app = webapp2.WSGIApplication([
    ('/', MainPage), 
    ('/FizzBuzz', FizzBuzz),
    ('/Ascii', Ascii),
    ('/blog', Blogfront),
    ('/blog/newpost', Blogpost),
], debug=True)