"""
Montreal Travel Companion - Final Production Version
All bugs fixed - Working preferences and notification system
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

Config.set('kivy', 'keyboard_mode', '')
Config.set('kivy', 'keyboard_layout', '')
Config.set('kivy', 'log_level', 'info')

from kivy.utils import platform
if platform not in ('android', 'ios'):
    Config.set('kivy', 'keyboard_mode', 'systemanddock')
    Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

# --- 2. Imports ---
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDRectangleFlatButton, MDIconButton
from kivymd.uix.boxlayout import MDBoxLayout
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
from kivy.properties import StringProperty, NumericProperty, DictProperty, BooleanProperty
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
    logger.warning("websocket-client not installed. Notifications will use polling.")

# --- 4. Window Configuration ---
if platform not in ('android', 'ios'):
    Window.size = (400, 800)
else:
    Window.softinput_mode = 'below_target'

# API Configuration - UPDATE WITH YOUR SERVER IP!
API_BASE_URL = "http://192.168.2.18:8000"  # Change to your server IP
WS_BASE_URL = "ws://192.168.2.18:8000"     # Change to your server IP

# --- 5. Color Scheme ---
COLORS = {
    'primary': (0.38, 0.49, 0.89, 1),
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
    'default': (0.95, 0.95, 0.95, 1)
}

TYPE_ICONS = {
    'restaurant': '🍽️', 'cafe': '☕', 'museum': '🏛️', 
    'park': '🌳', 'gym': '💪', 'bar': '🍺', 'default': '📍'
}

# --- 6. WebSocket Client ---

class NotificationClient:
    def __init__(self, user_id, on_notification, on_connection_change=None):
        self.user_id = user_id
        self.on_notification = on_notification
        self.on_connection_change = on_connection_change
        self.ws = None
        self.connected = False
        self.reconnect_attempts = 0
        self._stop_flag = False
        self._thread = None
    
    def connect(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_flag = False
        self._thread = threading.Thread(target=self._run_websocket, daemon=True)
        self._thread.start()
        logger.info(f"Starting WebSocket connection for {self.user_id}")
    
    def disconnect(self):
        self._stop_flag = True
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
        self.connected = False
    
    def _run_websocket(self):
        while not self._stop_flag and self.reconnect_attempts < 5:
            try:
                ws_url = f"{WS_BASE_URL}/ws/notifications/{self.user_id}"
                logger.info(f"Connecting to: {ws_url}")
                
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
        logger.info(f"WebSocket connected for {self.user_id}")
        if self.on_connection_change:
            Clock.schedule_once(lambda dt: self.on_connection_change(True), 0)
    
    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            logger.info(f"Notification received: {data.get('type')}")
            Clock.schedule_once(lambda dt: self.on_notification(data), 0)
        except Exception as e:
            logger.error(f"Error parsing notification: {e}")
    
    def _on_error(self, ws, error):
        logger.error(f"WebSocket error: {error}")
    
    def _on_close(self, ws, code, msg):
        self.connected = False
        logger.info(f"WebSocket closed: {code}")
        if self.on_connection_change:
            Clock.schedule_once(lambda dt: self.on_connection_change(False), 0)

# --- 7. Components ---

class RecommendationCard(MDCard):
    def __init__(self, rec_data, **kwargs):
        super().__init__(**kwargs)
        self.rec_data = rec_data
        self.orientation = 'vertical'
        self.adaptive_height = True
        self.size_hint_x = 1
        self.radius = [dp(12)]
        self.elevation = 2
        self.padding = dp(12)
        self.spacing = dp(6)
        
        # Color by type
        rec_type = rec_data.get('type', '').lower()
        self.md_bg_color = TYPE_COLORS.get(
            'restaurant' if 'restaurant' in rec_type else
            'cafe' if 'cafe' in rec_type else
            'museum' if 'museum' in rec_type else
            'park' if 'park' in rec_type else 'default'
        )
        
        self.build_content()
    
    def build_content(self):
        # Header
        header = MDBoxLayout(size_hint_y=None, height=dp(32))
        
        # Icon
        rec_type = self.rec_data.get('type', '').lower()
        icon = TYPE_ICONS.get(
            'restaurant' if 'restaurant' in rec_type else
            'cafe' if 'cafe' in rec_type else
            'museum' if 'museum' in rec_type else
            'park' if 'park' in rec_type else 'default'
        )
        
        header.add_widget(MDLabel(
            text=icon,
            font_size=sp(24),
            size_hint_x=None,
            width=dp(35)
        ))
        
        # Name
        name = self.rec_data.get('name', 'Unknown')
        header.add_widget(MDLabel(
            text=name[:28] + '...' if len(name) > 28 else name,
            font_style='H6',
            bold=True
        ))
        
        # Rating
        rating = self.rec_data.get('rating')
        if rating:
            header.add_widget(MDLabel(
                text=f"⭐{rating}",
                size_hint_x=None,
                width=dp(50),
                halign='right'
            ))
        
        self.add_widget(header)
        
        # Description
        desc = self.rec_data.get('description', '')
        if desc:
            self.add_widget(MDLabel(
                text=desc[:50] + '...' if len(desc) > 50 else desc,
                font_size=sp(12),
                theme_text_color='Secondary',
                size_hint_y=None,
                height=dp(20)
            ))
        
        # Reason
        reason = self.rec_data.get('reason', '')
        if reason:
            self.add_widget(MDLabel(
                text=f"💡 {reason[:60]}..." if len(reason) > 60 else f"💡 {reason}",
                font_size=sp(13),
                size_hint_y=None,
                height=dp(22)
            ))
        
        # Address
        address = self.rec_data.get('address', '')
        if address and address != 'Address not available':
            self.add_widget(MDLabel(
                text=f"📍 {address[:45]}..." if len(address) > 45 else f"📍 {address}",
                font_size=sp(11),
                theme_text_color='Secondary',
                size_hint_y=None,
                height=dp(18)
            ))
        
        # Bottom
        bottom = MDBoxLayout(size_hint_y=None, height=dp(35))
        
        # Distance
        distance = self.rec_data.get('distance', 0)
        if distance:
            dist_str = f"{distance/1000:.1f}km" if distance > 1000 else f"{distance}m"
            bottom.add_widget(MDLabel(
                text=f"{dist_str} away",
                font_size=sp(13)
            ))
        else:
            bottom.add_widget(MDWidget())
        
        # Navigate
        nav_btn = MDRaisedButton(
            text="NAVIGATE",
            size_hint_x=None,
            width=dp(90),
            on_release=self.navigate,
            md_bg_color=COLORS['primary']
        )
        bottom.add_widget(nav_btn)
        self.add_widget(bottom)
    
    def navigate(self, instance):
        lat = self.rec_data.get('latitude')
        lon = self.rec_data.get('longitude')
        name = self.rec_data.get('name', 'Destination')
        
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
            
            Snackbar(text=f"Opening navigation to {name}").open()
        else:
            Snackbar(text="Location not available").open()

class NotificationBanner(MDCard):
    def __init__(self, title, message, notif_type="info", **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint = (0.92, None)
        self.height = dp(70)
        self.pos_hint = {'center_x': 0.5, 'top': 0.98}
        self.radius = [dp(10)]
        self.elevation = 4
        
        # Colors by type
        colors = {
            "location_change": COLORS['primary'],
            "weather_change": COLORS['warning'],
            "meal_time": COLORS['success'],
            "time_period_change": COLORS['primary_light'],
            "preferences_updated": COLORS['accent'],
            "temperature_change": COLORS['error'],
            "default": COLORS['text_secondary']
        }
        self.md_bg_color = colors.get(notif_type, colors['default'])
        
        content = MDBoxLayout(padding=dp(8), spacing=dp(6))
        
        # Icon
        icons = {
            "location_change": "📍",
            "weather_change": "🌤️",
            "meal_time": "🍽️",
            "time_period_change": "🕐",
            "preferences_updated": "⚙️",
            "temperature_change": "🌡️",
            "default": "🔔"
        }
        
        content.add_widget(MDLabel(
            text=icons.get(notif_type, "🔔"),
            font_size=sp(22),
            size_hint_x=None,
            width=dp(32)
        ))
        
        # Text
        text_box = MDBoxLayout(orientation='vertical')
        text_box.add_widget(MDLabel(
            text=title,
            bold=True,
            text_color=(1, 1, 1, 1),
            font_size=sp(14)
        ))
        text_box.add_widget(MDLabel(
            text=message[:55] + "..." if len(message) > 55 else message,
            font_size=sp(11),
            text_color=(1, 1, 1, 0.9)
        ))
        content.add_widget(text_box)
        
        # Close
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

# --- 8. Screens ---

class WelcomeScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
    
    def build_ui(self):
        self.clear_widgets()
        layout = MDFloatLayout()
        
        with layout.canvas.before:
            Color(*COLORS['primary_light'])
            self.bg_rect = RoundedRectangle(pos=(0, 0), size=Window.size)
        
        content = MDBoxLayout(
            orientation='vertical',
            padding=dp(25),
            spacing=dp(15),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        
        content.add_widget(MDWidget(size_hint_y=0.1))
        
        content.add_widget(MDLabel(
            text='🗺️',
            halign='center',
            font_size=sp(75),
            size_hint_y=None,
            height=dp(90)
        ))
        
        content.add_widget(MDLabel(
            text='Montreal\nTravel Companion',
            font_size=sp(26),
            bold=True,
            halign='center',
            text_color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(70)
        ))
        
        content.add_widget(MDLabel(
            text='Your AI-powered local guide',
            font_size=sp(15),
            halign='center',
            text_color=(1, 1, 1, 0.85),
            size_hint_y=None,
            height=dp(25)
        ))
        
        content.add_widget(MDWidget(size_hint_y=0.1))
        
        btn = MDRaisedButton(
            text='START EXPLORING',
            size_hint_x=0.75,
            size_hint_y=None,
            height=dp(48),
            pos_hint={'center_x': 0.5},
            md_bg_color=COLORS['accent'],
            on_release=lambda x: self.go_next()
        )
        content.add_widget(btn)
        content.add_widget(MDWidget(size_hint_y=0.2))
        
        layout.add_widget(content)
        self.add_widget(layout)
    
    def go_next(self):
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
        
        toolbar = MDTopAppBar(
            title="Your Preferences",
            elevation=4,
            left_action_items=[["arrow-left", lambda x: self.go_back()]]
        )
        layout.add_widget(toolbar)
        
        scroll = MDScrollView()
        content = MDBoxLayout(
            orientation='vertical',
            spacing=dp(10),
            padding=dp(15),
            size_hint_y=None
        )
        content.bind(minimum_height=content.setter('height'))
        
        # User ID
        id_card = MDCard(
            orientation='vertical',
            padding=dp(12),
            radius=[dp(10)],
            elevation=2,
            size_hint_y=None,
            height=dp(110)
        )
        id_card.add_widget(MDLabel(
            text="👤 Profile",
            font_style='H6',
            bold=True,
            size_hint_y=None,
            height=dp(28)
        ))
        self.user_id_input = MDTextField(
            hint_text="Username",
            text="traveler1",
            mode="rectangle"
        )
        id_card.add_widget(self.user_id_input)
        content.add_widget(id_card)
        
        # Meal Times - FIXED LAYOUT
        meal_card = MDCard(
            orientation='vertical',
            padding=dp(12),
            radius=[dp(10)],
            elevation=2,
            size_hint_y=None,
            height=dp(210)
        )
        meal_card.add_widget(MDLabel(
            text="🍽️ Meal Schedule",
            font_style='H6',
            bold=True,
            size_hint_y=None,
            height=dp(28)
        ))
        
        # Breakfast
        b_box = MDBoxLayout(size_hint_y=None, height=dp(50))
        b_box.add_widget(MDLabel(text="Breakfast:", size_hint_x=0.35))
        self.input_breakfast = MDTextField(text="08:00", hint_text="HH:MM", mode="rectangle")
        b_box.add_widget(self.input_breakfast)
        meal_card.add_widget(b_box)
        
        # Lunch
        l_box = MDBoxLayout(size_hint_y=None, height=dp(50))
        l_box.add_widget(MDLabel(text="Lunch:", size_hint_x=0.35))
        self.input_lunch = MDTextField(text="12:00", hint_text="HH:MM", mode="rectangle")
        l_box.add_widget(self.input_lunch)
        meal_card.add_widget(l_box)
        
        # Dinner
        d_box = MDBoxLayout(size_hint_y=None, height=dp(50))
        d_box.add_widget(MDLabel(text="Dinner:", size_hint_x=0.35))
        self.input_dinner = MDTextField(text="19:00", hint_text="HH:MM", mode="rectangle")
        d_box.add_widget(self.input_dinner)
        meal_card.add_widget(d_box)
        
        content.add_widget(meal_card)
        
        # Activity
        act_card = MDCard(
            orientation='vertical',
            padding=dp(12),
            radius=[dp(10)],
            elevation=2,
            size_hint_y=None,
            height=dp(95)
        )
        act_card.add_widget(MDLabel(
            text="🎯 Activity Type",
            font_style='H6',
            bold=True,
            size_hint_y=None,
            height=dp(28)
        ))
        
        btn_box = MDBoxLayout(spacing=dp(8))
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
        
        # Cuisines - FIXED LAYOUT
        cuisine_card = MDCard(
            orientation='vertical',
            padding=dp(12),
            radius=[dp(10)],
            elevation=2,
            size_hint_y=None,
            height=dp(340)
        )
        cuisine_card.add_widget(MDLabel(
            text="🍴 Cuisines",
            font_style='H6',
            bold=True,
            size_hint_y=None,
            height=dp(28)
        ))
        
        self.cuisines = ['Italian', 'French', 'Japanese', 'Mexican', 'Burgers', 'Cafe']
        self.cuisine_checks = {}
        
        for cuisine in self.cuisines:
            row = MDBoxLayout(size_hint_y=None, height=dp(44), spacing=dp(5))
            chk = MDCheckbox(size_hint=(None, None), size=(dp(44), dp(44)))
            if cuisine == 'French':
                chk.active = True
            self.cuisine_checks[cuisine] = chk
            row.add_widget(chk)
            
            emojis = {'Italian': '🍝', 'French': '🥐', 'Japanese': '🍣',
                     'Mexican': '🌮', 'Burgers': '🍔', 'Cafe': '☕'}
            row.add_widget(MDLabel(
                text=f"{emojis.get(cuisine, '🍽️')} {cuisine}",
                font_size=sp(14)
            ))
            cuisine_card.add_widget(row)
        
        content.add_widget(cuisine_card)
        
        # Save
        save_btn = MDRaisedButton(
            text="SAVE & CONTINUE",
            size_hint_x=1,
            size_hint_y=None,
            height=dp(48),
            md_bg_color=COLORS['success'],
            on_release=self.save_prefs
        )
        content.add_widget(save_btn)
        content.add_widget(MDWidget(size_hint_y=None, height=dp(15)))
        
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
            Snackbar(text="Enter a username").open()
            return
        
        self.show_loading()
        threading.Thread(target=self.save_api, daemon=True).start()
    
    def save_api(self):
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
        except requests.exceptions.ConnectionError:
            Clock.schedule_once(lambda dt: self.on_error("Cannot connect to server. Is it running?"), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.on_error(str(e)), 0)
    
    def show_loading(self):
        self.dialog = MDDialog(
            text="Saving...",
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
        Snackbar(text=f"Error: {error}", duration=3).open()

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
        
        self.toolbar = MDTopAppBar(
            title="Discover Montreal",
            elevation=4,
            right_action_items=[
                ["refresh", lambda x: self.refresh_data()],
                ["bell", lambda x: self.show_notifs()],
                ["message-alert", lambda x: self.test_notification()],  # Test button
                ["cog", lambda x: self.go_settings()]
            ]
        )
        layout.add_widget(self.toolbar)
        
        # Status
        self.status_bar = MDBoxLayout(
            size_hint_y=None,
            height=dp(24),
            padding=(dp(12), 0)
        )
        self.status_label = MDLabel(
            text="● Connecting...",
            font_size=sp(11)
        )
        self.status_bar.add_widget(self.status_label)
        layout.add_widget(self.status_bar)
        
        scroll = MDScrollView()
        self.content = MDBoxLayout(
            orientation='vertical',
            spacing=dp(10),
            padding=dp(12),
            size_hint_y=None
        )
        self.content.bind(minimum_height=self.content.setter('height'))
        
        # Context
        self.context_card = MDCard(
            orientation='vertical',
            padding=dp(10),
            radius=[dp(10)],
            elevation=2,
            size_hint_y=None,
            height=dp(90)
        )
        self.context_card.add_widget(MDLabel(
            text="📍 Context",
            font_style='H6',
            bold=True,
            size_hint_y=None,
            height=dp(24)
        ))
        self.context_label = MDLabel(text="Loading...", theme_text_color='Secondary')
        self.context_card.add_widget(self.context_label)
        self.content.add_widget(self.context_card)
        
        self.content.add_widget(MDLabel(
            text="✨ Recommendations",
            font_style='H5',
            bold=True,
            size_hint_y=None,
            height=dp(32)
        ))
        
        self.recs_container = MDBoxLayout(
            orientation='vertical',
            spacing=dp(10),
            size_hint_y=None
        )
        self.recs_container.bind(minimum_height=self.recs_container.setter('height'))
        self.content.add_widget(self.recs_container)
        
        scroll.add_widget(self.content)
        layout.add_widget(scroll)
        self.add_widget(layout)
    
    def on_enter(self):
        app = MDApp.get_running_app()
        if app.user_id:
            if WEBSOCKET_AVAILABLE:
                self.start_ws()
            # Send context updates every 30s to trigger notifications
            self.context_timer = Clock.schedule_interval(self.send_context, 30)
        self.refresh_data()
    
    def on_leave(self):
        if hasattr(self, 'context_timer'):
            self.context_timer.cancel()
    
    def start_ws(self):
        app = MDApp.get_running_app()
        if self.notification_client:
            self.notification_client.disconnect()
        
        self.notification_client = NotificationClient(
            app.user_id,
            self.handle_notif,
            self.update_status
        )
        self.notification_client.connect()
    
    def update_status(self, connected):
        self.ws_connected = connected
        if connected:
            self.status_label.text = "● Live"
            self.status_label.text_color = COLORS['success']
            self.status_bar.md_bg_color = (0.92, 1, 0.92, 1)
        else:
            self.status_label.text = "● Offline"
            self.status_label.text_color = COLORS['error']
            self.status_bar.md_bg_color = (1, 0.92, 0.92, 1)
    
    def send_context(self, dt=None):
        """Send context update to trigger server notifications"""
        app = MDApp.get_running_app()
        if not app.user_id:
            return
        
        def _send():
            try:
                payload = {
                    "user_id": app.user_id,
                    "location": {
                        "latitude": app.latitude,
                        "longitude": app.longitude
                    },
                    "current_time": datetime.now().hour
                }
                
                response = requests.post(
                    f"{API_BASE_URL}/api/context/update",
                    json=payload,
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Handle any notifications from response
                    for notif in data.get('notifications', []):
                        Clock.schedule_once(lambda dt, n=notif: self.handle_notif(n), 0)
                        
            except Exception as e:
                logger.error(f"Context update failed: {e}")
        
        threading.Thread(target=_send, daemon=True).start()
    
    def handle_notif(self, data):
        """Handle notification - show banner and add to history"""
        notif_type = data.get('type', 'info')
        title = data.get('title', 'Notification')
        message = data.get('message', '')
        
        # Add to history
        self.notification_history.append({
            'type': notif_type,
            'title': title,
            'message': message,
            'timestamp': data.get('timestamp', datetime.now().isoformat())
        })
        
        if len(self.notification_history) > 50:
            self.notification_history = self.notification_history[-50:]
        
        # Show banner for all except connection/pong
        if notif_type not in ['connection_established', 'pong']:
            banner = NotificationBanner(title, message, notif_type)
            self.add_widget(banner)
            Clock.schedule_once(lambda dt: banner.dismiss() if banner.parent else None, 5)
            
            # Also show snackbar
            Snackbar(text=f"{title}: {message[:40]}...", duration=2).open()
            
            # Refresh for context changes
            if notif_type in ['location_change', 'weather_change', 'meal_time']:
                Clock.schedule_once(lambda dt: self.refresh_data(), 1)
    
    def test_notification(self):
        """Manually trigger test notification"""
        test_notifs = [
            {'type': 'meal_time', 'title': 'Lunch Time!', 
             'message': 'Check out nearby restaurants for lunch.'},
            {'type': 'weather_change', 'title': 'Weather Update',
             'message': 'Weather changed to sunny. Great for outdoor activities!'},
            {'type': 'location_change', 'title': 'New Area',
             'message': "You've moved to a new location. Discovering nearby places..."}
        ]
        
        import random
        test = random.choice(test_notifs)
        test['timestamp'] = datetime.now().isoformat()
        self.handle_notif(test)
    
    def refresh_data(self):
        app = MDApp.get_running_app()
        if not app.user_id:
            self.manager.current = 'preferences'
            return
        
        self.toolbar.title = "Updating..."
        threading.Thread(target=self.fetch, daemon=True).start()
    
    def fetch(self):
        app = MDApp.get_running_app()
        
        payload = {
            "preferences": app.preferences,
            "location": {"latitude": app.latitude, "longitude": app.longitude}
        }
        
        try:
            response = requests.post(f"{API_BASE_URL}/api/recommendations", json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                Clock.schedule_once(lambda dt: self.update_ui(data), 0)
            else:
                Clock.schedule_once(lambda dt: self.show_err(f"Error {response.status_code}"), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.show_err(str(e)), 0)
    
    def update_ui(self, data):
        self.toolbar.title = "Discover Montreal"
        
        # Context
        ctx = data.get('context', {})
        weather = ctx.get('weather', 'unknown')
        temp = ctx.get('temperature', 'N/A')
        period = ctx.get('time_period', 'N/A')
        
        app = MDApp.get_running_app()
        self.context_label.text = f"☀️ {weather} • {temp}°C • {period}\n📍 {app.latitude:.4f}, {app.longitude:.4f}"
        
        # Recommendations
        self.recs_container.clear_widgets()
        
        recs = data.get('recommendations', [])
        if not recs:
            self.recs_container.add_widget(MDLabel(
                text="No recommendations",
                halign='center',
                theme_text_color='Hint'
            ))
            return
        
        for rec in recs:
            card = RecommendationCard(rec)
            self.recs_container.add_widget(card)
    
    def show_err(self, error):
        self.toolbar.title = "Discover Montreal"
        Snackbar(text=f"Error: {error}").open()
    
    def show_notifs(self):
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
        
        toolbar = MDTopAppBar(
            title="Notifications",
            elevation=4,
            left_action_items=[["arrow-left", lambda x: self.go_back()]],
            right_action_items=[["delete", lambda x: self.clear()]]
        )
        layout.add_widget(toolbar)
        
        self.scroll = MDScrollView()
        self.list_container = MDBoxLayout(
            orientation='vertical',
            spacing=dp(8),
            padding=dp(12),
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
        notifs = main.notification_history
        
        if not notifs:
            card = MDCard(
                padding=dp(20),
                radius=[dp(10)],
                size_hint_y=None,
                height=dp(120)
            )
            card.add_widget(MDLabel(
                text="📭 No notifications",
                halign='center',
                font_style='H6'
            ))
            self.list_container.add_widget(card)
            return
        
        for notif in reversed(notifs):
            card = MDCard(
                padding=dp(10),
                radius=[dp(8)],
                size_hint_y=None,
                height=dp(70),
                elevation=1
            )
            
            card.add_widget(MDLabel(
                text=notif['title'],
                bold=True,
                size_hint_y=None,
                height=dp(22)
            ))
            card.add_widget(MDLabel(
                text=notif['message'][:70] + '...' if len(notif['message']) > 70 else notif['message'],
                theme_text_color='Secondary',
                font_size=sp(12)
            ))
            
            self.list_container.add_widget(card)
    
    def clear(self):
        main = self.manager.get_screen('main')
        main.notification_history = []
        self.refresh()
        Snackbar(text="Cleared").open()
    
    def go_back(self):
        self.manager.transition.direction = 'right'
        self.manager.current = 'main'

# --- 9. App ---

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
