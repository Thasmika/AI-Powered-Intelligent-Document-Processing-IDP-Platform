import sys
content = open('static/index.html', 'r', encoding='utf-8').read()

target = '<!-- View: Container Dashboard -->\\n            <div id="view-container-dashboard" class="view">'
content = content.replace(target, '<!-- Merged Container Dashboard -->')

content = content.replace("switchView('container-dashboard')", "switchView('main-dashboard')")

open('static/index.html', 'w', encoding='utf-8').write(content)
print('Successfully merged dashboards')
