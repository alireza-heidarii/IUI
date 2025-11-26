"""
Montreal Travel Companion - Production Android App
Complete working version with all error fixes
Compatible with KivyMD 1.2.0
"""

import os
import logging
import threading
import json
from datetime import datetime
import requests
import webbrowser

# --- 1. Environment Configuration ---
from kivy.config import Config

# Use native keyboard on mobile devices
Config.set('kivy', 'keyboard_mode', '')
Config.set('kivy', 'keyboard_layout', '')
Config.set('kivy', 'log_level', 'info')

# Desktop-specific settings
from kivy.utils import platform
if platform not in ('android', 'ios'):
    Config.set('kivy', 'keyboard_mode', 'systemanddock')
    Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

# --- 2. Imports ---
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDRectangleFlatButton, MDIconButton, MDFlatButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.card import MDCard
from kivymd.uix.textfield import MDTextField
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.dialog import MDDialog
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.widget import MDWidget
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.floatlayout import MDFloatLayout

from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty, DictProperty, ListProperty, BooleanProperty
from kivy.animation import Animation
from kivy.graphics import Color, RoundedRectangle

# --- 3. Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GPS Support
try:
    from plyer import gps
    if platform == 'android':
        from android.permissions import request_permissions, Permission
    GPS_AVAILABLE = True
except ImportError:
    GPS_AVAILABLE = False

# WebSocket Support
try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    logger.warning("websocket-client not installed")

# --- 4. Window Configuration ---
if platform not in ('android', 'ios'):
    Window.size = (400, 800)
else:
    Window.softinput_mode = 'below_target'

# API Configuration - CHANGE THIS TO YOUR IP
API_BASE_URL = "http://192.168.2.18:8000"
WS_BASE_URL = "ws://192.168.2.18:8000"

# --- 5. Design Constants ---
COLORS = {
    'primary': (0.38, 0.49, 0.89, 1),
    'primary_dark': (0.25, 0.32, 0.71, 1),
    'primary_light': (0.56, 0.64, 0.92, 1),
    'accent': (1, 0.45, 0.42, 1),
    'success': (0.30, 0.69, 0.31, 1),
    'warning': (1, 0.76, 0.03, 1),
    'error': (0.96, 0.26, 0.21, 1),
    'text_primary': (0.13, 0.13, 0.13, 1),
    'text_secondary': (0.38, 0.38, 0.38, 1),
    'background': (0.98, 0.98, 0.98, 1),
    'card_bg': (1, 1, 1, 1),
}

TYPE_COLORS = {
    'restaurant': (1, 0.92, 0.85, 1),
    'cafe': (0.95, 0.90, 0.85, 1),
    'museum': (0.88, 0.92, 1, 1),
    'park': (0.88, 0.96, 0.88, 1),
    'activity': (0.94, 0.90, 1, 1),
    'default': (0.95, 0.95, 0.95, 1)
}

TYPE_ICONS = {
    'restaurant': '🍽️',
    'cafe': '☕',
    'museum': '🏛️',
    'park': '🌳',
    'gym': '💪',
    'shopping': '🛍️',
    'bar': '🍺',
    'default': '📍'
}

# --- 6. Helper Functions ---

def get_responsive_padding():
    width = Window.width
    if width < 360:
        return dp(12)
    elif width < 400:
        return dp(14)
    return dp(16)

def get_responsive_spacing():
    width = Window.width
    if width < 360:
        return dp(8)
    elif width < 400:
        return dp(10)
    return dp(12)

# --- 7. WebSocket Client ---

class NotificationClient:
    def __init__(self, user_id, on_notification, on_connection_change=None):
        self.user_id = user_id
        self.on_notification = on_notification
        self.on_connection_change = on_connection_change
        self.ws = None
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self._stop_flag = False
        self._thread = None
    
    def connect(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_flag = False
        self._thread = threading.Thread(target=self._run_websocket, daemon=True)
        self._thread.start()
    
    def disconnect(self):
        self._stop_flag = True
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
        self.connected = False
    
    def _run_websocket(self):
        while not self._stop_flag and self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                ws_url = f"{WS_BASE_URL}/ws/notifications/{self.user_id}"
                self.ws = websocket.WebSocketApp(
                    ws_url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close
                )
                self.ws.run_forever(ping_interval=30, ping_timeout=10)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
            
            if not self._stop_flag:
                self.reconnect_attempts += 1
                import time
                time.sleep(3)
    
    def _on_open(self, ws):
        self.connected = True
        self.reconnect_attempts = 0
        if self.on_connection_change:
            Clock.schedule_once(lambda dt: self.on_connection_change(True), 0)
    
    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            Clock.schedule_once(lambda dt: self.on_notification(data), 0)
        except:
            pass
    
    def _on_error(self, ws, error):
        logger.error(f"WebSocket error: {error}")
    
    def _on_close(self, ws, code, msg):
        self.connected = False
        if self.on_connection_change:
            Clock.schedule_once(lambda dt: self.on_connection_change(False), 0)

# --- 8. Custom Components ---

class RecommendationCard(MDCard):
    def __init__(self, rec_data, **kwargs):
        super().__init__(**kwargs)
        self.rec_data = rec_data
        self.orientation = 'vertical'
        self.adaptive_height = True
        self.size_hint_x = 1
        self.radius = [dp(12)]
        self.elevation = 2
        self.padding = get_responsive_padding()
        self.spacing = dp(8)
        
        # Get card color based on type
        rec_type = rec_data.get('type', '').lower()
        for key in TYPE_COLORS:
            if key in rec_type:
                self.md_bg_color = TYPE_COLORS[key]
                break
        else:
            self.md_bg_color = TYPE_COLORS['default']
        
        self.build_content()
    
    def build_content(self):
        # Header with icon and name
        header = MDBoxLayout(size_hint_y=None, height=dp(35))
        
        # Icon
        rec_type = self.rec_data.get('type', '').lower()
        icon = '📍'
        for key, val in TYPE_ICONS.items():
            if key in rec_type:
                icon = val
                break
        
        header.add_widget(MDLabel(
            text=icon,
            font_size=sp(24),
            size_hint_x=None,
            width=dp(35)
        ))
        
        # Name
        name = self.rec_data.get('name', 'Unknown')
        header.add_widget(MDLabel(
            text=name[:30] + '...' if len(name) > 30 else name,
            font_style='H6',
            bold=True,
            theme_text_color='Primary'
        ))
        
        # Rating
        rating = self.rec_data.get('rating')
        if rating:
            header.add_widget(MDLabel(
                text=f"⭐ {rating}",
                size_hint_x=None,
                width=dp(60),
                halign='right',
                theme_text_color='Secondary'
            ))
        
        self.add_widget(header)
        
        # Description
        desc = self.rec_data.get('description', '')
        if desc and desc != 'Unknown':
            self.add_widget(MDLabel(
                text=desc[:60] + '...' if len(desc) > 60 else desc,
                font_size=sp(12),
                theme_text_color='Secondary',
                size_hint_y=None,
                height=dp(20)
            ))
        
        # Reason
        reason = self.rec_data.get('reason', '')
        if reason:
            self.add_widget(MDLabel(
                text=f"💡 {reason[:70]}..." if len(reason) > 70 else f"💡 {reason}",
                font_size=sp(13),
                theme_text_color='Primary',
                size_hint_y=None,
                height=dp(25)
            ))
        
        # Address
        address = self.rec_data.get('address', '')
        if address and address != 'Address not available':
            addr_text = address[:50] + '...' if len(address) > 50 else address
            self.add_widget(MDLabel(
                text=f"📍 {addr_text}",
                font_size=sp(11),
                theme_text_color='Secondary',
                size_hint_y=None,
                height=dp(20)
            ))
        
        # Bottom row
        bottom = MDBoxLayout(size_hint_y=None, height=dp(40))
        
        # Distance
        distance = self.rec_data.get('distance', 0)
        if distance:
            dist_str = f"{distance/1000:.1f}km" if distance > 1000 else f"{distance}m"
            bottom.add_widget(MDLabel(
                text=f"{dist_str} away",
                theme_text_color='Primary',
                font_size=sp(13)
            ))
        else:
            bottom.add_widget(MDWidget())
        
        # Navigate button
        nav_btn = MDRaisedButton(
            text="NAVIGATE",
            size_hint_x=None,
            width=dp(100),
            on_release=self.navigate,
            md_bg_color=COLORS['primary']
        )
        bottom.add_widget(nav_btn)
        
        self.add_widget(bottom)
    
    def navigate(self, instance):
        lat = self.rec_data.get('latitude')
        lon = self.rec_data.get('longitude')
        
        if lat and lon:
            maps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"
            
            if platform == 'android':
                try:
                    from jnius import autoclass
                    PythonActivity = autoclass('org.kivy.android.PythonActivity')
                    Intent = autoclass('android.content.Intent')
                    Uri = autoclass('android.net.Uri')
                    
                    intent = Intent(Intent.ACTION_VIEW, Uri.parse(maps_url))
                    intent.setPackage("com.google.android.apps.maps")
                    PythonActivity.mActivity.startActivity(intent)
                except:
                    webbrowser.open(maps_url)
            else:
                webbrowser.open(maps_url)
            
            Snackbar(text=f"Opening navigation...").open()
        else:
            Snackbar(text="Location not available").open()

class NotificationBanner(MDCard):
    def __init__(self, title, message, notif_type="info", **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint = (0.94, None)
        self.height = dp(75)
        self.pos_hint = {'center_x': 0.5, 'top': 0.98}
        self.radius = [dp(12)]
        self.elevation = 4
        
        colors = {
            "location_change": COLORS['primary'],
            "weather_change": COLORS['warning'],
            "meal_time": COLORS['success'],
            "default": COLORS['text_secondary']
        }
        self.md_bg_color = colors.get(notif_type, colors['default'])
        
        content = MDBoxLayout(padding=dp(10), spacing=dp(8))
        
        # Icon
        icons = {
            "location_change": "📍",
            "weather_change": "🌤️",
            "meal_time": "🍽️",
            "default": "🔔"
        }
        content.add_widget(MDLabel(
            text=icons.get(notif_type, "🔔"),
            font_size=sp(24),
            size_hint_x=None,
            width=dp(35)
        ))
        
        # Text
        text_box = MDBoxLayout(orientation='vertical')
        text_box.add_widget(MDLabel(
            text=title,
            bold=True,
            text_color=(1, 1, 1, 1)
        ))
        text_box.add_widget(MDLabel(
            text=message[:60] + "..." if len(message) > 60 else message,
            font_size=sp(12),
            text_color=(1, 1, 1, 0.9)
        ))
        content.add_widget(text_box)
        
        # Close button
        close_btn = MDIconButton(
            icon="close",
            theme_text_color='Custom',
            text_color=(1, 1, 1, 1),
            on_release=self.dismiss
        )
        content.add_widget(close_btn)
        
        self.add_widget(content)
    
    def dismiss(self, *args):
        anim = Animation(opacity=0, duration=0.3)
        anim.bind(on_complete=lambda *x: self.parent.remove_widget(self) if self.parent else None)
        anim.start(self)

# --- 9. Screens ---

class WelcomeScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
    
    def build_ui(self):
        self.clear_widgets()
        
        layout = MDFloatLayout()
        
        # Background
        with layout.canvas.before:
            Color(*COLORS['primary_light'])
            self.bg_rect = RoundedRectangle(pos=(0, 0), size=Window.size)
        
        # Content
        content = MDBoxLayout(
            orientation='vertical',
            padding=dp(30),
            spacing=dp(20),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        
        content.add_widget(MDWidget(size_hint_y=0.1))
        
        # Logo
        content.add_widget(MDLabel(
            text='🗺️',
            halign='center',
            font_size=sp(80),
            size_hint_y=None,
            height=dp(100)
        ))
        
        # Title
        content.add_widget(MDLabel(
            text='Montreal\nTravel Companion',
            font_size=sp(28),
            bold=True,
            halign='center',
            text_color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(80)
        ))
        
        # Subtitle
        content.add_widget(MDLabel(
            text='Your AI-powered local guide',
            font_size=sp(16),
            halign='center',
            text_color=(1, 1, 1, 0.85),
            size_hint_y=None,
            height=dp(30)
        ))
        
        content.add_widget(MDWidget(size_hint_y=0.1))
        
        # Start button
        btn = MDRaisedButton(
            text='START EXPLORING',
            size_hint_x=0.8,
            size_hint_y=None,
            height=dp(50),
            pos_hint={'center_x': 0.5},
            md_bg_color=COLORS['accent'],
            on_release=self.go_next
        )
        content.add_widget(btn)
        
        content.add_widget(MDWidget(size_hint_y=0.2))
        
        layout.add_widget(content)
        self.add_widget(layout)
    
    def go_next(self, instance):
        self.manager.transition.direction = 'left'
        self.manager.current = 'preferences'

class PreferencesScreen(MDScreen):
    activity_type = StringProperty("outdoor")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
    
    def build_ui(self):
        self.clear_widgets()
        
        layout = MDBoxLayout(orientation='vertical')
        
        # Toolbar
        toolbar = MDTopAppBar(
            title="Your Preferences",
            elevation=4,
            left_action_items=[["arrow-left", lambda x: self.go_back()]]
        )
        layout.add_widget(toolbar)
        
        # Content
        scroll = MDScrollView()
        content = MDBoxLayout(
            orientation='vertical',
            spacing=get_responsive_spacing(),
            padding=get_responsive_padding(),
            size_hint_y=None
        )
        content.bind(minimum_height=content.setter('height'))
        
        # User ID Card
        id_card = MDCard(
            orientation='vertical',
            padding=dp(15),
            radius=[dp(12)],
            elevation=2,
            size_hint_y=None,
            height=dp(120)
        )
        id_card.add_widget(MDLabel(
            text="👤 Your Profile",
            font_style='H6',
            bold=True,
            size_hint_y=None,
            height=dp(30)
        ))
        self.user_id_input = MDTextField(
            hint_text="Enter username",
            text="traveler1",
            mode="rectangle"
        )
        id_card.add_widget(self.user_id_input)
        content.add_widget(id_card)
        
        # Meal Times
        meal_card = MDCard(
            orientation='vertical',
            padding=dp(15),
            radius=[dp(12)],
            elevation=2,
            size_hint_y=None,
            height=dp(200)
        )
        meal_card.add_widget(MDLabel(
            text="🍽️ Meal Times",
            font_style='H6',
            bold=True,
            size_hint_y=None,
            height=dp(30)
        ))
        
        self.input_breakfast = MDTextField(
            text="08:00",
            hint_text="Breakfast",
            mode="rectangle"
        )
        self.input_lunch = MDTextField(
            text="12:00",
            hint_text="Lunch",
            mode="rectangle"
        )
        self.input_dinner = MDTextField(
            text="19:00",
            hint_text="Dinner",
            mode="rectangle"
        )
        
        meal_card.add_widget(self.input_breakfast)
        meal_card.add_widget(self.input_lunch)
        meal_card.add_widget(self.input_dinner)
        content.add_widget(meal_card)
        
        # Activity Type
        act_card = MDCard(
            orientation='vertical',
            padding=dp(15),
            radius=[dp(12)],
            elevation=2,
            size_hint_y=None,
            height=dp(100)
        )
        act_card.add_widget(MDLabel(
            text="🎯 Activity Preference",
            font_style='H6',
            bold=True,
            size_hint_y=None,
            height=dp(30)
        ))
        
        btn_box = MDBoxLayout(spacing=dp(10))
        self.btn_indoor = MDRectangleFlatButton(
            text="🏠 Indoor",
            on_release=lambda x: self.set_activity("indoor")
        )
        self.btn_outdoor = MDRaisedButton(
            text="🌳 Outdoor",
            on_release=lambda x: self.set_activity("outdoor")
        )
        btn_box.add_widget(self.btn_indoor)
        btn_box.add_widget(self.btn_outdoor)
        act_card.add_widget(btn_box)
        content.add_widget(act_card)
        
        # Cuisines
        cuisine_card = MDCard(
            orientation='vertical',
            padding=dp(15),
            radius=[dp(12)],
            elevation=2,
            size_hint_y=None,
            height=dp(350)
        )
        cuisine_card.add_widget(MDLabel(
            text="🍴 Favorite Cuisines",
            font_style='H6',
            bold=True,
            size_hint_y=None,
            height=dp(30)
        ))
        
        self.cuisines = ['Italian', 'French', 'Japanese', 'Mexican', 'Burgers', 'Cafe']
        self.cuisine_checks = {}
        
        for cuisine in self.cuisines:
            row = MDBoxLayout(size_hint_y=None, height=dp(45))
            chk = MDCheckbox(size_hint=(None, None), size=(dp(45), dp(45)))
            if cuisine == 'French':
                chk.active = True
            self.cuisine_checks[cuisine] = chk
            row.add_widget(chk)
            row.add_widget(MDLabel(text=cuisine))
            cuisine_card.add_widget(row)
        
        content.add_widget(cuisine_card)
        
        # Save button
        save_btn = MDRaisedButton(
            text="SAVE & CONTINUE",
            size_hint_x=1,
            size_hint_y=None,
            height=dp(50),
            md_bg_color=COLORS['success'],
            on_release=self.save_prefs
        )
        content.add_widget(save_btn)
        
        content.add_widget(MDWidget(size_hint_y=None, height=dp(20)))
        
        scroll.add_widget(content)
        layout.add_widget(scroll)
        self.add_widget(layout)
    
    def set_activity(self, activity):
        self.activity_type = activity
        if activity == "indoor":
            self.btn_indoor.md_bg_color = COLORS['primary']
            self.btn_outdoor.md_bg_color = (0, 0, 0, 0)
        else:
            self.btn_outdoor.md_bg_color = COLORS['primary']
            self.btn_indoor.md_bg_color = (0, 0, 0, 0)
    
    def go_back(self):
        self.manager.transition.direction = 'right'
        self.manager.current = 'welcome'
    
    def save_prefs(self, instance):
        if not self.user_id_input.text.strip():
            Snackbar(text="Please enter a username").open()
            return
        
        self.show_loading()
        threading.Thread(target=self.save_to_api, daemon=True).start()
    
    def save_to_api(self):
        user_id = self.user_id_input.text.strip()
        
        payload = {
            "user_id": user_id,
            "activity_type": self.activity_type,
            "meal_times": {
                "breakfast": self.input_breakfast.text,
                "lunch": self.input_lunch.text,
                "dinner": self.input_dinner.text
            },
            "preferred_cuisines": [k for k, v in self.cuisine_checks.items() if v.active]
        }
        
        app = MDApp.get_running_app()
        app.user_id = user_id
        app.preferences = payload
        
        try:
            response = requests.post(f"{API_BASE_URL}/api/preferences", json=payload, timeout=5)
            if response.status_code == 200:
                Clock.schedule_once(self.on_success, 0)
            else:
                Clock.schedule_once(lambda dt: self.on_error(f"Error {response.status_code}"), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.on_error(str(e)), 0)
    
    def show_loading(self):
        self.dialog = MDDialog(
            text="Saving preferences...",
            type="custom",
            content_cls=MDProgressBar(type="indeterminate")
        )
        self.dialog.open()
    
    def on_success(self, dt):
        if hasattr(self, 'dialog'):
            self.dialog.dismiss()
        self.manager.transition.direction = 'left'
        self.manager.current = 'main'
    
    def on_error(self, error):
        if hasattr(self, 'dialog'):
            self.dialog.dismiss()
        Snackbar(text=f"Error: {error}").open()

class MainScreen(MDScreen):
    ws_connected = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.notification_client = None
        self.notification_history = []
        self.build_ui()
    
    def build_ui(self):
        self.clear_widgets()
        
        layout = MDBoxLayout(orientation='vertical')
        
        # Toolbar
        self.toolbar = MDTopAppBar(
            title="Discover Montreal",
            elevation=4,
            right_action_items=[
                ["refresh", lambda x: self.refresh_data()],
                ["bell", lambda x: self.show_notifications()],
                ["cog", lambda x: self.go_settings()]
            ]
        )
        layout.add_widget(self.toolbar)
        
        # Status bar
        self.status_bar = MDBoxLayout(
            size_hint_y=None,
            height=dp(25),
            padding=(dp(15), 0),
            md_bg_color=(0.92, 1, 0.92, 1)
        )
        self.status_label = MDLabel(
            text="● Connected",
            font_size=sp(11),
            text_color=COLORS['success']
        )
        self.status_bar.add_widget(self.status_label)
        layout.add_widget(self.status_bar)
        
        # Content
        scroll = MDScrollView()
        self.content = MDBoxLayout(
            orientation='vertical',
            spacing=get_responsive_spacing(),
            padding=get_responsive_padding(),
            size_hint_y=None
        )
        self.content.bind(minimum_height=self.content.setter('height'))
        
        # Context card
        self.context_card = MDCard(
            orientation='vertical',
            padding=dp(15),
            radius=[dp(12)],
            elevation=2,
            size_hint_y=None,
            height=dp(100)
        )
        self.context_card.add_widget(MDLabel(
            text="📍 Current Context",
            font_style='H6',
            bold=True,
            size_hint_y=None,
            height=dp(25)
        ))
        self.context_label = MDLabel(
            text="Loading...",
            theme_text_color='Secondary'
        )
        self.context_card.add_widget(self.context_label)
        self.content.add_widget(self.context_card)
        
        # Recommendations header
        self.content.add_widget(MDLabel(
            text="✨ Recommendations",
            font_style='H5',
            bold=True,
            size_hint_y=None,
            height=dp(35)
        ))
        
        # Recommendations container
        self.recs_container = MDBoxLayout(
            orientation='vertical',
            spacing=get_responsive_spacing(),
            size_hint_y=None
        )
        self.recs_container.bind(minimum_height=self.recs_container.setter('height'))
        self.content.add_widget(self.recs_container)
        
        scroll.add_widget(self.content)
        layout.add_widget(scroll)
        self.add_widget(layout)
    
    def on_enter(self):
        app = MDApp.get_running_app()
        if app.user_id and WEBSOCKET_AVAILABLE:
            self.start_websocket()
        self.refresh_data()
    
    def start_websocket(self):
        app = MDApp.get_running_app()
        if self.notification_client:
            self.notification_client.disconnect()
        
        self.notification_client = NotificationClient(
            app.user_id,
            self.handle_notification,
            self.update_status
        )
        self.notification_client.connect()
    
    def update_status(self, connected):
        self.ws_connected = connected
        if connected:
            self.status_label.text = "● Live Updates"
            self.status_label.text_color = COLORS['success']
        else:
            self.status_label.text = "● Offline"
            self.status_label.text_color = COLORS['error']
    
    def handle_notification(self, data):
        notif_type = data.get('type', 'info')
        title = data.get('title', 'Notification')
        message = data.get('message', '')
        
        self.notification_history.append({
            'type': notif_type,
            'title': title,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
        
        if notif_type not in ['connection_established', 'pong']:
            banner = NotificationBanner(title, message, notif_type)
            self.add_widget(banner)
            Clock.schedule_once(lambda dt: banner.dismiss(), 4)
    
    def refresh_data(self):
        app = MDApp.get_running_app()
        if not app.user_id:
            self.manager.current = 'preferences'
            return
        
        self.toolbar.title = "Updating..."
        threading.Thread(target=self.fetch_data, daemon=True).start()
    
    def fetch_data(self):
        app = MDApp.get_running_app()
        
        payload = {
            "preferences": app.preferences,
            "location": {
                "latitude": app.latitude,
                "longitude": app.longitude
            }
        }
        
        try:
            response = requests.post(f"{API_BASE_URL}/api/recommendations", json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                Clock.schedule_once(lambda dt: self.update_ui(data), 0)
            else:
                Clock.schedule_once(lambda dt: self.show_error(f"Error {response.status_code}"), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.show_error(str(e)), 0)
    
    def update_ui(self, data):
        self.toolbar.title = "Discover Montreal"
        
        # Update context
        context = data.get('context', {})
        weather = context.get('weather', 'unknown')
        temp = context.get('temperature', 'N/A')
        period = context.get('time_period', 'N/A')
        
        app = MDApp.get_running_app()
        self.context_label.text = f"☀️ {weather} • {temp}°C • {period}\n📍 {app.latitude:.4f}, {app.longitude:.4f}"
        
        # Update recommendations
        self.recs_container.clear_widgets()
        
        recs = data.get('recommendations', [])
        if not recs:
            self.recs_container.add_widget(MDLabel(
                text="No recommendations available",
                halign='center',
                theme_text_color='Hint'
            ))
            return
        
        for rec in recs:
            card = RecommendationCard(rec)
            self.recs_container.add_widget(card)
    
    def show_error(self, error):
        self.toolbar.title = "Discover Montreal"
        Snackbar(text=f"Error: {error}").open()
    
    def show_notifications(self):
        self.manager.transition.direction = 'left'
        self.manager.current = 'notifications'
    
    def go_settings(self):
        self.manager.transition.direction = 'right'
        self.manager.current = 'preferences'

class NotificationScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
    
    def build_ui(self):
        self.clear_widgets()
        
        layout = MDBoxLayout(orientation='vertical')
        
        # Toolbar
        toolbar = MDTopAppBar(
            title="Notifications",
            elevation=4,
            left_action_items=[["arrow-left", lambda x: self.go_back()]],
            right_action_items=[["delete", lambda x: self.clear_all()]]
        )
        layout.add_widget(toolbar)
        
        # List
        self.scroll = MDScrollView()
        self.list_container = MDBoxLayout(
            orientation='vertical',
            spacing=get_responsive_spacing(),
            padding=get_responsive_padding(),
            size_hint_y=None
        )
        self.list_container.bind(minimum_height=self.list_container.setter('height'))
        self.scroll.add_widget(self.list_container)
        layout.add_widget(self.scroll)
        
        self.add_widget(layout)
    
    def on_enter(self):
        self.refresh()
    
    def refresh(self):
        self.list_container.clear_widgets()
        
        main = self.manager.get_screen('main')
        notifications = main.notification_history
        
        if not notifications:
            card = MDCard(
                orientation='vertical',
                padding=dp(20),
                radius=[dp(12)],
                size_hint_y=None,
                height=dp(150)
            )
            card.add_widget(MDLabel(
                text="📭 No notifications yet",
                halign='center',
                font_style='H6'
            ))
            self.list_container.add_widget(card)
            return
        
        for notif in reversed(notifications):
            card = MDCard(
                orientation='vertical',
                padding=dp(12),
                radius=[dp(8)],
                size_hint_y=None,
                height=dp(80),
                elevation=1
            )
            
            card.add_widget(MDLabel(
                text=notif['title'],
                bold=True,
                size_hint_y=None,
                height=dp(25)
            ))
            card.add_widget(MDLabel(
                text=notif['message'][:80] + '...' if len(notif['message']) > 80 else notif['message'],
                theme_text_color='Secondary'
            ))
            
            self.list_container.add_widget(card)
    
    def clear_all(self):
        main = self.manager.get_screen('main')
        main.notification_history = []
        self.refresh()
        Snackbar(text="Cleared all notifications").open()
    
    def go_back(self):
        self.manager.transition.direction = 'right'
        self.manager.current = 'main'

# --- 10. Main App ---

class MontrealCompanionApp(MDApp):
    user_id = StringProperty(None)
    preferences = DictProperty({})
    latitude = NumericProperty(45.5017)
    longitude = NumericProperty(-73.5673)
    
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.accent_palette = "Red"
        self.theme_cls.theme_style = "Light"
        
        sm = MDScreenManager()
        sm.add_widget(WelcomeScreen(name='welcome'))
        sm.add_widget(PreferencesScreen(name='preferences'))
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(NotificationScreen(name='notifications'))
        
        return sm
    
    def on_start(self):
        if GPS_AVAILABLE:
            try:
                if platform == 'android':
                    request_permissions([Permission.ACCESS_FINE_LOCATION])
                gps.configure(on_location=self.on_gps_location)
                gps.start(minTime=10000, minDistance=10)
            except:
                pass
    
    def on_gps_location(self, **kwargs):
        self.latitude = kwargs.get('lat', self.latitude)
        self.longitude = kwargs.get('lon', self.longitude)
    
    def on_stop(self):
        try:
            main = self.root.get_screen('main')
            if main.notification_client:
                main.notification_client.disconnect()
        except:
            pass

if __name__ == '__main__':
    MontrealCompanionApp().run()
