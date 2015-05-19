import webapp2
import jinja2
import os

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

app = webapp2.WSGIApplication([
    ('/', MainPage), 
    ('/FizzBuzz', FizzBuzz),
    ('/Ascii', Ascii),
], debug=True)