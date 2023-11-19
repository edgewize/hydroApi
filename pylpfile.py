import pylp
import sass


pylp.task('default', lambda:
    sass.compile(dirname=('src/styles', 'static/css'), output_style='compressed')
)