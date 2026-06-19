import os
os.chdir('/Users/duchaochao/Desktop/power_market_dashboard')
with open('app.py', 'r') as f:
    content = f.read()
content = content.replace('mod-card mod-card-map', 'mod-card')
with open('app.py', 'w') as f:
    f.write(content)
print('Done: removed mod-card-map class')
