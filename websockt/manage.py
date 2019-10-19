import web
from run_websockt import WebSockt
from multiprocessing import Process


urls = ("/.*", "hello")
app = web.application(urls, globals())
render = web.template.render('templates/')




class hello:
    def GET(self):
        return render.index()


if __name__ == "__main__":

    p1 = Process(target=WebSockt().run)
    p2 = Process(target=app.run)
    p1.start()
    p2.start()
