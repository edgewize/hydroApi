import pylp
import sass


pylp.task('default', lambda:
    sass.compile(dirname=('src/styles', 'hydroApp/static/css'), output_style='compressed')
)


