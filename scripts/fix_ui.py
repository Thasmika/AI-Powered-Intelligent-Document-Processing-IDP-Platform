import sys
import re

try:
    content = open('static/index.html', 'r', encoding='utf-8').read()

    # 1. Extract Hero Section
    hero_start = content.find('<!-- Hero Section for First Impression -->')
    hero_end = content.find('<!-- KPI Summary Cards -->')
    if hero_start == -1 or hero_end == -1:
        print("Hero section not found")
        sys.exit(1)
    hero_section = content[hero_start:hero_end]

    # 2. Extract Container Dashboard Card
    container_start = content.find('<div id="view-container-dashboard" class="view">')
    if container_start == -1:
        print("Container dashboard not found")
        sys.exit(1)
    
    # The card inside container dashboard
    card_start = content.find('<div class="card">', container_start)
    
    # Find the end of view-container-dashboard
    explorer_start = content.find('<!-- View: Explorer -->')
    if explorer_start == -1:
        print("Explorer not found")
        sys.exit(1)
    
    # We want everything from card_start to just before explorer_start, minus the closing </div> of the view
    container_section = content[card_start:explorer_start]
    # Remove the last </div> which belongs to view-container-dashboard
    last_div_idx = container_section.rfind('</div>')
    if last_div_idx != -1:
        container_section = container_section[:last_div_idx] + container_section[last_div_idx+6:]

    # 3. Create new view-main-dashboard
    new_main_dashboard = f'''<!-- View: Main Dashboard -->
            <div id="view-main-dashboard" class="view active">
                {hero_section}
                {container_section}
            </div>
            
            '''

    # 4. Find the start of view-main-dashboard in original content
    main_start = content.find('<!-- View: Main Dashboard -->')
    if main_start == -1:
        print("Main dashboard not found")
        sys.exit(1)

    # 5. Replace everything from main_start to explorer_start
    new_content = content[:main_start] + new_main_dashboard + content[explorer_start:]

    # 6. Add "Process Pending Scans" button next to "Refresh"
    # Find the Refresh button in the new_content
    target_btn = '<button class="btn" onclick="fetchDocuments()">Refresh</button>'
    replacement_btn = '''<div style="display: flex; gap: 10px;">
                            <button class="btn btn-outline" onclick="triggerIngestion()">Process Pending Scans</button>
                            <button class="btn" onclick="fetchDocuments()">Refresh</button>
                        </div>'''
    new_content = new_content.replace(target_btn, replacement_btn)

    # 7. Update sidebar navigation
    new_content = new_content.replace("switchView('container-dashboard')", "switchView('main-dashboard')")
    
    # 8. Remove mock fallback in fetchDocuments if it exists
    # We'll just explicitly replace fetchDocuments
    fetch_start = new_content.find('async function fetchDocuments() {')
    fetch_end = new_content.find('async function fetchExceptions() {')
    if fetch_start != -1 and fetch_end != -1:
        new_fetch = '''async function fetchDocuments() {
            try {
                const res = await fetch(`${API_BASE}/documents`, {
                    headers: {'Authorization': `Bearer ${TOKEN}`}
                });
                const docs = await res.json();
                renderTable('dashboard-table-body', docs);
            } catch (e) {
                console.error(e);
            }
        }
        
        '''
        new_content = new_content[:fetch_start] + new_fetch + new_content[fetch_end:]

    open('static/index.html', 'w', encoding='utf-8').write(new_content)
    print("Successfully fixed UI!")

except Exception as e:
    print(f"Error: {e}")
