import folium
from branca.element import Template, MacroElement
from folium import Map, features

def add_legend_and_stats(folium_map, stats):
    legend_html = f'''
     <div style="position: fixed; 
     bottom: 50px; left: 50px; width: 250px; height: 130px; 
     background-color: white;
     border:2px solid grey; z-index:9999; font-size:14px;
     padding: 10px;">
     <b>Elevation Stats</b><br>
     Min: {stats['min']} m<br>
     Max: {stats['max']} m<br>
     Mean: {stats['mean']:.2f} m<br>
     Std Dev: {stats['std_dev']:.2f}
     </div>
    '''
    folium_map.get_root().html.add_child(folium.Element(legend_html))


