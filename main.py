"""
Montreal Travel Companion - Production Android App
Beautiful Material Design 3 UI with Full Navigation Support
Enhanced cards with all recommendation data and responsive design
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

# --- 2. Critical Font Fix ---
from kivy.core.text import LabelBase
try:
    import kivymd
    base_path = os.path.dirname(kivymd.__file__)
    
    possible_paths = [
        os.path.join(base_path, 'fonts', 'materialdesignicons-webfont.ttf'),
        os.path.join(base_path, 'fonts', 'MaterialIcons-Regular.ttf'),
    ]
    
    font_path = None
    for path in possible_paths:
        if os.path.exists(path):
            font_path = path
            break
            
    if font_path:
        LabelBase.register(name='MaterialIcons', fn_regular=font_path)
        LabelBase.register(name='Icon', fn_regular=font_path)

except ImportError:
    print("[CRITICAL] KivyMD is not installed. Please run: pip install kivymd")

# --- 3. Imports ---
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
from kivymd.uix.list import MDList, TwoLineAvatarIconListItem, IconLeftWidget, IconRightWidget
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.relativelayout import MDRelativeLayout

from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty, DictProperty, ListProperty, BooleanProperty
from kivy.animation import Animation
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.uix.behaviors import TouchRippleBehavior

# --- 4. Setup ---
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
    logger.warning("websocket-client not installed. Install with: pip install websocket-client")

# --- 5. Window Configuration ---
if platform not in ('android', 'ios'):
    Window.size = (400, 800)
else:
    from kivy.core.window import Window
    Window.softinput_mode = 'below_target'

# API Configuration
API_BASE_URL = "http://192.168.2.18:8000"  # Replace with your IP
WS_BASE_URL = "ws://192.168.2.18:8000"

# --- 6. Design Constants ---
COLORS = {
    'primary': (0.38, 0.49, 0.89, 1),      # Beautiful blue
    'primary_dark': (0.25, 0.32, 0.71, 1),
    'primary_light': (0.56, 0.64, 0.92, 1),
    'accent': (1, 0.45, 0.42, 1),          # Coral
    'success': (0.30, 0.69, 0.31, 1),      # Green
    'warning': (1, 0.76, 0.03, 1),         # Amber
    'error': (0.96, 0.26, 0.21, 1),        # Red
    'text_primary': (0.13, 0.13, 0.13, 1),
    'text_secondary': (0.38, 0.38, 0.38, 1),
    'text_hint': (0.6, 0.6, 0.6, 1),
    'background': (0.98, 0.98, 0.98, 1),
    'card_bg': (1, 1, 1, 1),
    'divider': (0.88, 0.88, 0.88, 1)
}

# Type colors for recommendation cards
TYPE_COLORS = {
    'restaurant': (1, 0.92, 0.85, 1),      # Warm peach
    'cafe': (0.95, 0.90, 0.85, 1),         # Coffee cream
    'museum': (0.88, 0.92, 1, 1),          # Light blue
    'park': (0.88, 0.96, 0.88, 1),         # Light green
    'activity': (0.94, 0.90, 1, 1),        # Light purple
    'shopping': (1, 0.90, 0.95, 1),        # Light pink
    'entertainment': (0.92, 0.88, 1, 1),   # Lavender
    'gym': (0.85, 0.95, 0.92, 1),          # Mint
    'bar': (0.95, 0.88, 0.88, 1),          # Rose
    'default': (0.95, 0.95, 0.95, 1)       # Light gray
}

# Type icons
TYPE_ICONS = {
    'restaurant': '🍽️',
    'cafe': '☕',
    'museum': '🏛️',
    'park': '🌳',
    'gym': '💪',
    'shopping': '🛍️',
    'movie_theater': '🎬',
    'bar': '🍺',
    'night_club': '🎉',
    'library': '📚',
    'aquarium': '🐠',
    'zoo': '🦁',
    'beach': '🏖️',
    'default': '📍'
}

# --- 7. Responsive Helpers ---

def get_responsive_font(base_size):
    """Calculate responsive font size."""
    width = Window.width
    if width < 360:
        return sp(base_size * 0.85)
    elif width < 400:
        return sp(base_size * 0.95)
    elif width > 600:
        return sp(base_size * 1.1)
    return sp(base_size)

def get_responsive_padding():
    """Calculate responsive padding."""
    width = Window.width
    if width < 360:
        return dp(12)
    elif width < 400:
        return dp(14)
    elif width > 600:
        return dp(20)
    return dp(16)

def get_responsive_spacing():
    """Calculate responsive spacing."""
    width = Window.width
    if width < 360:
        return dp(8)
    elif width < 400:
        return dp(10)
    elif width > 600:
        return dp(14)
    return dp(12)

# --- 8. WebSocket Notification Client ---

class NotificationClient:
    """WebSocket client for real-time notifications."""
    
    def __init__(self, user_id, on_notification_callback, on_connection_change_callback=None):
        self.user_id = user_id
        self.on_notification = on_notification_callback
        self.on_connection_change = on_connection_change_callback
        self.ws = None
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 3
        self._stop_flag = False
        self._thread = None
    
    def connect(self):
        """Start WebSocket connection in background thread."""
        if self._thread and self._thread.is_alive():
            return
        
        self._stop_flag = False
        self._thread = threading.Thread(target=self._run_websocket, daemon=True)
        self._thread.start()
    
    def disconnect(self):
        """Stop WebSocket connection."""
        self._stop_flag = True
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
        self.connected = False
        if self.on_connection_change:
            Clock.schedule_once(lambda dt: self.on_connection_change(False), 0)
    
    def _run_websocket(self):
        """Main WebSocket loop."""
        while not self._stop_flag and self.reconnect_attempts < self.max_reconnect_attempts:
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
                time.sleep(self.reconnect_delay)
    
    def _on_open(self, ws):
        self.connected = True
        self.reconnect_attempts = 0
        logger.info(f"WebSocket connected for {self.user_id}")
        if self.on_connection_change:
            Clock.schedule_once(lambda dt: self.on_connection_change(True), 0)
    
    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            Clock.schedule_once(lambda dt: self.on_notification(data), 0)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse: {e}")
    
    def _on_error(self, ws, error):
        logger.error(f"WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        self.connected = False
        if self.on_connection_change:
            Clock.schedule_once(lambda dt: self.on_connection_change(False), 0)

# --- 9. Beautiful Custom Components ---

class GradientCard(MDCard):
    """Beautiful gradient card with shadow."""
    
    def __init__(self, gradient_colors=None, **kwargs):
        super().__init__(**kwargs)
        self.radius = [dp(16)]
        self.elevation = 3
        
        if gradient_colors:
            with self.canvas.before:
                Color(*gradient_colors[0])
                self.rect = RoundedRectangle(
                    pos=self.pos,
                    size=self.size,
                    radius=[dp(16)]
                )
            self.bind(pos=self.update_rect, size=self.update_rect)
    
    def update_rect(self, *args):
        if hasattr(self, 'rect'):
            self.rect.pos = self.pos
            self.rect.size = self.size


class BeautifulRecommendationCard(MDCard):
    """Enhanced recommendation card with all data displayed beautifully."""
    
    def __init__(self, rec_data, on_navigate=None, **kwargs):
        super().__init__(**kwargs)
        self.rec_data = rec_data
        self.on_navigate_callback = on_navigate
        self.orientation = 'vertical'
        self.adaptive_height = True
        self.size_hint_x = 1
        self.radius = [dp(16)]
        self.elevation = 2
        self.spacing = dp(8)
        
        # Determine card type and color
        rec_type = rec_data.get('type', '').lower()
        bg_color = self._get_type_color(rec_type)
        self.md_bg_color = bg_color
        
        self.build_card_content()
    
    def _get_type_color(self, rec_type):
        """Get background color based on type."""
        for key in TYPE_COLORS:
            if key in rec_type:
                return TYPE_COLORS[key]
        return TYPE_COLORS['default']
    
    def _get_type_icon(self, rec_type):
        """Get icon based on type."""
        for key in TYPE_ICONS:
            if key in rec_type:
                return TYPE_ICONS[key]
        return TYPE_ICONS['default']
    
    def build_card_content(self):
        """Build the card with all recommendation data."""
        padding = get_responsive_padding()
        
        # Main container with padding
        container = MDBoxLayout(
            orientation='vertical',
            padding=padding,
            spacing=dp(6),
            adaptive_height=True
        )
        
        # Header row with icon, name, and rating
        header = MDBoxLayout(
            size_hint_y=None,
            height=dp(32),
            spacing=dp(8)
        )
        
        # Type icon
        icon = self._get_type_icon(self.rec_data.get('type', ''))
        header.add_widget(MDLabel(
            text=icon,
            font_size=sp(24),
            size_hint_x=None,
            width=dp(32),
            halign='center'
        ))
        
        # Name (expandable)
        name = self.rec_data.get('name', 'Unknown')
        header.add_widget(MDLabel(
            text=name,
            font_style='H6',
            font_size=get_responsive_font(16),
            bold=True,
            theme_text_color='Primary',
            shorten=True,
            shorten_from='right',
            markup=True
        ))
        
        # Rating badge
        rating = self.rec_data.get('rating')
        if rating:
            rating_box = MDBoxLayout(
                size_hint_x=None,
                width=dp(60)
            )
            rating_box.add_widget(MDLabel(
                text=f"⭐ {rating}",
                font_size=sp(13),
                bold=True,
                theme_text_color='Custom',
                text_color=COLORS['text_primary']
            ))
            header.add_widget(rating_box)
        else:
            header.add_widget(MDWidget())  # Spacer
        
        container.add_widget(header)
        
        # Type/Category tags
        description = self.rec_data.get('description', '')
        if description:
            tags_box = MDBoxLayout(
                size_hint_y=None,
                height=dp(24),
                spacing=dp(6)
            )
            
            # Parse categories from description
            categories = [cat.strip() for cat in description.split(',')[:3]]
            for cat in categories:
                if cat and cat != 'Unknown':
                    tag_label = MDLabel(
                        text=f"[{cat.replace('_', ' ').title()}]",
                        font_size=sp(11),
                        theme_text_color='Custom',
                        text_color=COLORS['text_secondary'],
                        size_hint_x=None,
                        width=dp(len(cat) * 8 + 16)
                    )
                    tags_box.add_widget(tag_label)
            
            tags_box.add_widget(MDWidget())  # Fill remaining space
            container.add_widget(tags_box)
        
        # Reason for recommendation
        reason = self.rec_data.get('reason', '')
        if reason:
            reason_box = MDBoxLayout(
                size_hint_y=None,
                adaptive_height=True,
                padding=(dp(4), 0)
            )
            reason_box.add_widget(MDLabel(
                text=f"[b]Why:[/b] {reason}",
                font_size=get_responsive_font(13),
                theme_text_color='Secondary',
                markup=True,
                adaptive_height=True
            ))
            container.add_widget(reason_box)
        
        # Divider
        container.add_widget(MDWidget(
            size_hint_y=None,
            height=dp(1),
            md_bg_color=COLORS['divider']
        ))
        
        # Address
        address = self.rec_data.get('address', 'Address not available')
        if address and address != 'Address not available':
            # Shorten long addresses
            if len(address) > 60:
                address = address[:57] + "..."
            
            addr_box = MDBoxLayout(
                size_hint_y=None,
                adaptive_height=True,
                spacing=dp(4)
            )
            addr_box.add_widget(MDLabel(
                text="📍",
                size_hint_x=None,
                width=dp(20),
                font_size=sp(14)
            ))
            addr_box.add_widget(MDLabel(
                text=address,
                font_size=get_responsive_font(12),
                theme_text_color='Secondary',
                adaptive_height=True
            ))
            container.add_widget(addr_box)
        
        # Bottom row with distance and navigation
        bottom_row = MDBoxLayout(
            size_hint_y=None,
            height=dp(40),
            spacing=dp(8)
        )
        
        # Distance badge
        distance = self.rec_data.get('distance', 0)
        if distance:
            if distance > 1000:
                dist_str = f"{distance/1000:.1f} km away"
            else:
                dist_str = f"{distance} m away"
            
            dist_label = MDLabel(
                text=f"[b]{dist_str}[/b]",
                font_size=get_responsive_font(13),
                theme_text_color='Primary',
                markup=True,
                valign='center'
            )
            bottom_row.add_widget(dist_label)
        else:
            bottom_row.add_widget(MDWidget())  # Spacer
        
        # Navigate button
        nav_btn = MDRaisedButton(
            text="NAVIGATE",
            font_size=get_responsive_font(12),
            size_hint_x=None,
            width=dp(100),
            height=dp(32),
            md_bg_color=COLORS['primary'],
            on_release=self.navigate
        )
        
        # Add ripple effect
        nav_btn.bind(on_press=self.animate_press)
        
        bottom_row.add_widget(nav_btn)
        container.add_widget(bottom_row)
        
        self.add_widget(container)
        
        # Bind minimum height for adaptive sizing
        container.bind(minimum_height=lambda w, h: setattr(self, 'height', h + dp(8)))
    
    def animate_press(self, widget):
        """Animate button press."""
        anim = Animation(scale_x=0.95, scale_y=0.95, duration=0.1)
        anim += Animation(scale_x=1, scale_y=1, duration=0.1)
        anim.start(widget)
    
    def navigate(self, instance):
        """Handle navigation button press."""
        lat = self.rec_data.get('latitude')
        lon = self.rec_data.get('longitude')
        name = self.rec_data.get('name', 'Destination')
        
        if lat and lon:
            # Create Google Maps URL
            maps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}&travelmode=driving"
            
            # For Android, try to open in Google Maps app first
            if platform == 'android':
                try:
                    from jnius import autoclass, cast
                    PythonActivity = autoclass('org.kivy.android.PythonActivity')
                    Intent = autoclass('android.content.Intent')
                    Uri = autoclass('android.net.Uri')
                    
                    intent = Intent(Intent.ACTION_VIEW, Uri.parse(maps_url))
                    intent.setPackage("com.google.android.apps.maps")
                    
                    currentActivity = cast('android.app.Activity', PythonActivity.mActivity)
                    currentActivity.startActivity(intent)
                except:
                    # Fallback to browser
                    webbrowser.open(maps_url)
            else:
                # Desktop - open in browser
                webbrowser.open(maps_url)
            
            # Show feedback
            Snackbar(
                text=f"Opening navigation to {name}",
                snackbar_x="10dp",
                snackbar_y="10dp",
                bg_color=COLORS['success']
            ).open()
        else:
            Snackbar(
                text="Location coordinates not available",
                bg_color=COLORS['error']
            ).open()
        
        if self.on_navigate_callback:
            self.on_navigate_callback(self.rec_data)


class AnimatedNotificationBanner(MDCard):
    """Animated notification banner with slide-in effect."""
    
    def __init__(self, title, message, notif_type="info", **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint = (0.94, None)
        self.height = dp(80)
        self.pos_hint = {'center_x': 0.5, 'y': Window.height}  # Start above screen
        self.radius = [dp(16)]
        self.elevation = 6
        
        # Color schemes for different notification types
        colors = {
            "location_change": COLORS['primary'],
            "weather_change": COLORS['warning'],
            "meal_time": COLORS['success'],
            "temperature_change": COLORS['error'],
            "preferences_updated": COLORS['accent'],
            "connection_established": COLORS['success'],
            "default": COLORS['text_secondary']
        }
        
        self.md_bg_color = colors.get(notif_type, colors['default'])
        
        # Icon mapping
        icons = {
            "location_change": "📍",
            "weather_change": "🌤️",
            "meal_time": "🍽️",
            "temperature_change": "🌡️",
            "preferences_updated": "⚙️",
            "connection_established": "✅"
        }
        
        icon = icons.get(notif_type, "🔔")
        
        # Content
        content = MDBoxLayout(
            orientation='horizontal',
            padding=dp(12),
            spacing=dp(10)
        )
        
        # Icon
        content.add_widget(MDLabel(
            text=icon,
            font_size=sp(28),
            size_hint_x=None,
            width=dp(40),
            halign='center',
            valign='center'
        ))
        
        # Text
        text_box = MDBoxLayout(orientation='vertical')
        text_box.add_widget(MDLabel(
            text=title,
            font_size=get_responsive_font(15),
            bold=True,
            text_color=(1, 1, 1, 1)
        ))
        text_box.add_widget(MDLabel(
            text=message[:80] + "..." if len(message) > 80 else message,
            font_size=get_responsive_font(13),
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
    
    def show(self):
        """Animate the banner sliding in from top."""
        anim = Animation(
            pos_hint={'center_x': 0.5, 'top': 0.98},
            duration=0.3,
            transition='out_cubic'
        )
        anim.start(self)
        
        # Auto-dismiss after 4 seconds
        Clock.schedule_once(lambda dt: self.dismiss(), 4)
    
    def dismiss(self, *args):
        """Animate the banner sliding out."""
        anim = Animation(
            pos_hint={'center_x': 0.5, 'y': Window.height},
            duration=0.3,
            transition='in_cubic'
        )
        anim.bind(on_complete=lambda *x: self.parent.remove_widget(self) if self.parent else None)
        anim.start(self)


# --- 10. Screen Classes ---

class WelcomeScreen(MDScreen):
    """Beautiful animated welcome screen."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
    
    def build_ui(self):
        self.clear_widgets()
        
        # Gradient background
        layout = MDFloatLayout()
        
        # Background gradient effect
        with layout.canvas.before:
            Color(*COLORS['primary_light'])
            self.bg_rect = RoundedRectangle(
                pos=(0, 0),
                size=Window.size,
                radius=[0]
            )
        
        # Content container
        content = MDBoxLayout(
            orientation='vertical',
            padding=get_responsive_padding() * 2,
            spacing=get_responsive_spacing() * 2,
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        
        content.add_widget(MDWidget(size_hint_y=0.1))
        
        # Animated logo
        logo_container = MDBoxLayout(
            size_hint_y=None,
            height=dp(120),
            pos_hint={'center_x': 0.5}
        )
        
        self.logo = MDLabel(
            text='🗺️',
            halign='center',
            font_size=sp(90),
            size_hint=(None, None),
            size=(dp(100), dp(100)),
            pos_hint={'center_x': 0.5}
        )
        logo_container.add_widget(self.logo)
        content.add_widget(logo_container)
        
        # App title
        content.add_widget(MDLabel(
            text='[b]Montreal[/b]\n[size=24]Travel Companion[/size]',
            font_size=sp(32),
            halign='center',
            theme_text_color='Custom',
            text_color=(1, 1, 1, 1),
            markup=True,
            size_hint_y=None,
            height=dp(100)
        ))
        
        # Subtitle
        content.add_widget(MDLabel(
            text='Your AI-powered local guide',
            font_size=get_responsive_font(16),
            halign='center',
            theme_text_color='Custom',
            text_color=(1, 1, 1, 0.85),
            size_hint_y=None,
            height=dp(30)
        ))
        
        content.add_widget(MDWidget(size_hint_y=0.15))
        
        # Start button with animation
        self.start_btn = MDRaisedButton(
            text='BEGIN JOURNEY',
            font_size=get_responsive_font(18),
            size_hint_x=0.8,
            size_hint_y=None,
            height=dp(56),
            pos_hint={'center_x': 0.5},
            md_bg_color=COLORS['accent'],
            elevation=8,
            on_release=self.go_to_preferences
        )
        content.add_widget(self.start_btn)
        
        content.add_widget(MDWidget(size_hint_y=0.2))
        
        layout.add_widget(content)
        self.add_widget(layout)
        
        # Start animations
        Clock.schedule_once(self.animate_entrance, 0.1)
    
    def animate_entrance(self, dt):
        """Animate logo on entrance."""
        # Logo pulse animation
        anim = Animation(scale_x=1.1, scale_y=1.1, duration=0.8, transition='out_sine')
        anim += Animation(scale_x=1, scale_y=1, duration=0.8, transition='in_sine')
        anim.repeat = True
        anim.start(self.logo)
        
        # Button entrance
        self.start_btn.opacity = 0
        Animation(opacity=1, duration=0.5).start(self.start_btn)
    
    def go_to_preferences(self, instance):
        self.manager.transition.direction = 'left'
        self.manager.current = 'preferences'


class PreferencesScreen(MDScreen):
    """Beautiful preference input screen."""
    activity_type = StringProperty("outdoor")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
    
    def build_ui(self):
        self.clear_widgets()
        
        layout = MDBoxLayout(orientation='vertical')
        
        # Beautiful toolbar
        self.toolbar = MDTopAppBar(
            title="Personalize Your Experience",
            elevation=4,
            md_bg_color=COLORS['primary'],
            specific_text_color=(1, 1, 1, 1),
            left_action_items=[["arrow-left", lambda x: self.go_back()]]
        )
        layout.add_widget(self.toolbar)
        
        # Scrollable content
        scroll = MDScrollView()
        content = MDBoxLayout(
            orientation='vertical',
            spacing=get_responsive_spacing(),
            padding=get_responsive_padding(),
            size_hint_y=None,
            md_bg_color=COLORS['background']
        )
        content.bind(minimum_height=content.setter('height'))
        
        # User ID Card with gradient
        id_card = GradientCard(gradient_colors=[COLORS['primary_light'], COLORS['primary']])
        id_card.orientation = 'vertical'
        id_card.padding = get_responsive_padding()
        id_card.spacing = dp(8)
        id_card.adaptive_height = True
        
        id_card.add_widget(MDLabel(
            text="👤 Your Profile",
            font_style='H6',
            font_size=get_responsive_font(18),
            bold=True,
            text_color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(30)
        ))
        
        self.user_id_input = MDTextField(
            hint_text="Enter your username",
            mode="rectangle",
            text="traveler1",
            font_size=get_responsive_font(16),
            size_hint_x=1
        )
        id_card.add_widget(self.user_id_input)
        content.add_widget(id_card)
        
        # Meal Times Card
        meal_card = MDCard(
            orientation='vertical',
            padding=get_responsive_padding(),
            spacing=dp(12),
            radius=[dp(16)],
            elevation=2,
            adaptive_height=True,
            md_bg_color=COLORS['card_bg']
        )
        
        meal_card.add_widget(MDLabel(
            text="🍽️ Your Meal Schedule",
            font_style='H6',
            font_size=get_responsive_font(18),
            bold=True,
            theme_text_color='Primary',
            size_hint_y=None,
            height=dp(30)
        ))
        
        # Beautiful meal time inputs
        meals_data = [
            ("🌅 Breakfast", "08:00", "input_breakfast"),
            ("☀️ Lunch", "12:00", "input_lunch"),
            ("🌙 Dinner", "19:00", "input_dinner")
        ]
        
        for label, default_time, attr_name in meals_data:
            meal_row = MDBoxLayout(
                size_hint_y=None,
                height=dp(50),
                spacing=dp(10)
            )
            
            meal_row.add_widget(MDLabel(
                text=label,
                font_size=get_responsive_font(15),
                size_hint_x=0.4
            ))
            
            field = MDTextField(
                text=default_time,
                hint_text="HH:MM",
                mode="rectangle",
                font_size=get_responsive_font(15),
                size_hint_x=0.6
            )
            setattr(self, attr_name, field)
            meal_row.add_widget(field)
            
            meal_card.add_widget(meal_row)
        
        content.add_widget(meal_card)
        
        # Activity Type Card with beautiful toggle
        activity_card = MDCard(
            orientation='vertical',
            padding=get_responsive_padding(),
            spacing=dp(12),
            radius=[dp(16)],
            elevation=2,
            adaptive_height=True,
            md_bg_color=COLORS['card_bg']
        )
        
        activity_card.add_widget(MDLabel(
            text="🎯 Activity Preference",
            font_style='H6',
            font_size=get_responsive_font(18),
            bold=True,
            theme_text_color='Primary',
            size_hint_y=None,
            height=dp(30)
        ))
        
        btn_container = MDBoxLayout(
            spacing=dp(10),
            size_hint_y=None,
            height=dp(56)
        )
        
        self.btn_indoor = MDRaisedButton(
            text="🏠 Indoor",
            font_size=get_responsive_font(15),
            md_bg_color=COLORS['primary_light'],
            on_release=lambda x: self.set_activity("indoor")
        )
        
        self.btn_outdoor = MDRaisedButton(
            text="🌳 Outdoor",
            font_size=get_responsive_font(15),
            md_bg_color=COLORS['primary'],
            on_release=lambda x: self.set_activity("outdoor")
        )
        
        btn_container.add_widget(self.btn_indoor)
        btn_container.add_widget(self.btn_outdoor)
        activity_card.add_widget(btn_container)
        content.add_widget(activity_card)
        
        # Cuisine Preferences Card
        cuisine_card = MDCard(
            orientation='vertical',
            padding=get_responsive_padding(),
            spacing=dp(12),
            radius=[dp(16)],
            elevation=2,
            adaptive_height=True,
            md_bg_color=COLORS['card_bg']
        )
        
        cuisine_card.add_widget(MDLabel(
            text="🍴 Favorite Cuisines",
            font_style='H6',
            font_size=get_responsive_font(18),
            bold=True,
            theme_text_color='Primary',
            size_hint_y=None,
            height=dp(30)
        ))
        
        self.cuisines = ['Italian', 'French', 'Japanese', 'Mexican', 'Chinese', 
                        'Thai', 'Indian', 'Burgers', 'Pizza', 'Seafood', 'Cafe']
        self.cuisine_checks = {}
        
        cuisines_grid = MDGridLayout(
            cols=2 if Window.width >= 400 else 1,
            spacing=dp(8),
            adaptive_height=True
        )
        
        cuisine_emojis = {
            'Italian': '🍝', 'French': '🥐', 'Japanese': '🍣',
            'Mexican': '🌮', 'Chinese': '🥟', 'Thai': '🍜',
            'Indian': '🍛', 'Burgers': '🍔', 'Pizza': '🍕',
            'Seafood': '🦐', 'Cafe': '☕'
        }
        
        for cuisine in self.cuisines:
            row = MDBoxLayout(
                size_hint_y=None,
                height=dp(48),
                spacing=dp(8)
            )
            
            checkbox = MDCheckbox(
                size_hint=(None, None),
                size=(dp(48), dp(48)),
                active=(cuisine == 'French')  # Default selection
            )
            self.cuisine_checks[cuisine] = checkbox
            
            row.add_widget(checkbox)
            row.add_widget(MDLabel(
                text=f"{cuisine_emojis.get(cuisine, '🍽️')} {cuisine}",
                font_size=get_responsive_font(15),
                theme_text_color='Primary'
            ))
            
            cuisines_grid.add_widget(row)
        
        cuisine_card.add_widget(cuisines_grid)
        content.add_widget(cuisine_card)
        
        # Save button
        save_btn = MDRaisedButton(
            text="SAVE & START EXPLORING",
            font_size=get_responsive_font(16),
            size_hint_x=1,
            size_hint_y=None,
            height=dp(56),
            md_bg_color=COLORS['success'],
            elevation=4,
            on_release=self.save_preferences
        )
        content.add_widget(save_btn)
        
        content.add_widget(MDWidget(size_hint_y=None, height=dp(20)))
        
        scroll.add_widget(content)
        layout.add_widget(scroll)
        self.add_widget(layout)
    
    def set_activity(self, activity_type):
        """Update activity type selection."""
        self.activity_type = activity_type
        if activity_type == "indoor":
            self.btn_indoor.md_bg_color = COLORS['primary']
            self.btn_outdoor.md_bg_color = COLORS['primary_light']
        else:
            self.btn_outdoor.md_bg_color = COLORS['primary']
            self.btn_indoor.md_bg_color = COLORS['primary_light']
    
    def go_back(self):
        self.manager.transition.direction = 'right'
        self.manager.current = 'welcome'
    
    def save_preferences(self, instance):
        """Save preferences to API."""
        if not self.user_id_input.text.strip():
            Snackbar(
                text="Please enter a username",
                bg_color=COLORS['error']
            ).open()
            return
        
        self.show_loading()
        threading.Thread(target=self.save_to_api, daemon=True).start()
    
    def save_to_api(self):
        """API call to save preferences."""
        user_id = self.user_id_input.text.strip()
        
        payload = {
            "user_id": user_id,
            "activity_type": self.activity_type,
            "meal_times": {
                "breakfast": self.input_breakfast.text.strip(),
                "lunch": self.input_lunch.text.strip(),
                "dinner": self.input_dinner.text.strip()
            },
            "preferred_cuisines": [k for k, v in self.cuisine_checks.items() if v.active]
        }
        
        app = MDApp.get_running_app()
        app.user_id = user_id
        app.preferences = payload
        
        try:
            response = requests.post(f"{API_BASE_URL}/api/preferences", json=payload, timeout=5)
            if response.status_code == 200:
                Clock.schedule_once(self.on_save_success, 0)
            else:
                Clock.schedule_once(lambda dt: self.on_save_error(f"Error {response.status_code}"), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.on_save_error(str(e)), 0)
    
    def show_loading(self):
        """Show loading dialog."""
        progress = MDProgressBar(type="indeterminate")
        self.loading_dialog = MDDialog(
            text="Saving your preferences...",
            type="custom",
            content_cls=progress
        )
        self.loading_dialog.open()
    
    def on_save_success(self, dt):
        """Handle successful save."""
        if hasattr(self, 'loading_dialog'):
            self.loading_dialog.dismiss()
        
        Snackbar(
            text="Preferences saved successfully!",
            bg_color=COLORS['success']
        ).open()
        
        self.manager.transition.direction = 'left'
        self.manager.current = 'main'
    
    def on_save_error(self, error):
        """Handle save error."""
        if hasattr(self, 'loading_dialog'):
            self.loading_dialog.dismiss()
        
        Snackbar(
            text=f"Failed to save: {error}",
            bg_color=COLORS['error']
        ).open()


class MainScreen(MDScreen):
    """Beautiful main dashboard with recommendations."""
    
    ws_connected = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.notification_client = None
        self.notification_history = []
        self.build_ui()
    
    def build_ui(self):
        self.clear_widgets()
        
        layout = MDBoxLayout(orientation='vertical')
        
        # Beautiful toolbar
        self.toolbar = MDTopAppBar(
            title="Discover Montreal",
            elevation=4,
            md_bg_color=COLORS['primary'],
            specific_text_color=(1, 1, 1, 1),
            right_action_items=[
                ["refresh", lambda x: self.refresh_data()],
                ["bell", lambda x: self.show_notifications()],
                ["cog", lambda x: self.go_to_settings()]
            ]
        )
        layout.add_widget(self.toolbar)
        
        # Connection status bar
        self.status_bar = MDBoxLayout(
            size_hint_y=None,
            height=dp(30),
            padding=(get_responsive_padding(), 0),
            md_bg_color=(0.92, 1, 0.92, 1)
        )
        
        self.status_label = MDLabel(
            text="● Connected",
            font_size=get_responsive_font(12),
            theme_text_color='Custom',
            text_color=COLORS['success']
        )
        self.status_bar.add_widget(self.status_label)
        layout.add_widget(self.status_bar)
        
        # Main content scroll
        scroll = MDScrollView()
        self.content = MDBoxLayout(
            orientation='vertical',
            spacing=get_responsive_spacing(),
            padding=get_responsive_padding(),
            size_hint_y=None,
            md_bg_color=COLORS['background']
        )
        self.content.bind(minimum_height=self.content.setter('height'))
        
        # Context Card
        self.context_card = MDCard(
            orientation='vertical',
            padding=get_responsive_padding(),
            spacing=dp(8),
            radius=[dp(16)],
            elevation=2,
            adaptive_height=True,
            md_bg_color=COLORS['card_bg']
        )
        
        self.context_card.add_widget(MDLabel(
            text="📍 Current Context",
            font_style='H6',
            font_size=get_responsive_font(18),
            bold=True,
            theme_text_color='Primary',
            size_hint_y=None,
            height=dp(30)
        ))
        
        self.context_label = MDLabel(
            text="Loading...",
            font_size=get_responsive_font(14),
            theme_text_color='Secondary',
            adaptive_height=True
        )
        self.context_card.add_widget(self.context_label)
        self.content.add_widget(self.context_card)
        
        # Recommendations header
        header_box = MDBoxLayout(
            size_hint_y=None,
            height=dp(40),
            padding=(0, dp(10), 0, 0)
        )
        header_box.add_widget(MDLabel(
            text="✨ Personalized for You",
            font_style='H5',
            font_size=get_responsive_font(20),
            bold=True,
            theme_text_color='Primary'
        ))
        self.content.add_widget(header_box)
        
        # Recommendations container
        self.recs_container = MDBoxLayout(
            orientation='vertical',
            spacing=get_responsive_spacing(),
            size_hint_y=None,
            adaptive_height=True
        )
        self.recs_container.bind(minimum_height=self.recs_container.setter('height'))
        self.content.add_widget(self.recs_container)
        
        scroll.add_widget(self.content)
        layout.add_widget(scroll)
        self.add_widget(layout)
    
    def on_enter(self):
        """Called when entering the screen."""
        app = MDApp.get_running_app()
        
        if app.user_id and WEBSOCKET_AVAILABLE:
            self.start_websocket()
        
        # Schedule periodic context updates
        self.context_timer = Clock.schedule_interval(self.update_context, 60)
        self.refresh_data()
    
    def on_leave(self):
        """Called when leaving the screen."""
        if hasattr(self, 'context_timer'):
            self.context_timer.cancel()
    
    def start_websocket(self):
        """Start WebSocket connection."""
        app = MDApp.get_running_app()
        
        if self.notification_client:
            self.notification_client.disconnect()
        
        self.notification_client = NotificationClient(
            user_id=app.user_id,
            on_notification_callback=self.handle_notification,
            on_connection_change_callback=self.update_connection_status
        )
        self.notification_client.connect()
    
    def update_connection_status(self, connected):
        """Update connection status display."""
        self.ws_connected = connected
        if connected:
            self.status_label.text = "● Live Updates Active"
            self.status_label.text_color = COLORS['success']
            self.status_bar.md_bg_color = (0.92, 1, 0.92, 1)
        else:
            self.status_label.text = "● Reconnecting..."
            self.status_label.text_color = COLORS['warning']
            self.status_bar.md_bg_color = (1, 0.97, 0.92, 1)
    
    def handle_notification(self, data):
        """Handle incoming notification."""
        notif_type = data.get('type', 'info')
        title = data.get('title', 'Notification')
        message = data.get('message', '')
        
        # Store in history
        self.notification_history.append({
            'type': notif_type,
            'title': title,
            'message': message,
            'timestamp': data.get('timestamp', datetime.now().isoformat())
        })
        
        # Keep only last 50
        if len(self.notification_history) > 50:
            self.notification_history = self.notification_history[-50:]
        
        # Show banner for important notifications
        if notif_type not in ['connection_established', 'pong']:
            banner = AnimatedNotificationBanner(title, message, notif_type)
            self.add_widget(banner)
            banner.show()
            
            # Refresh data for context changes
            if notif_type in ['location_change', 'weather_change', 'meal_time']:
                Clock.schedule_once(lambda dt: self.refresh_data(), 1)
    
    def update_context(self, dt=None):
        """Send context update to server."""
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
                
                requests.post(f"{API_BASE_URL}/api/context/update", json=payload, timeout=5)
            except:
                pass
        
        threading.Thread(target=_send, daemon=True).start()
    
    def refresh_data(self):
        """Refresh recommendations from API."""
        app = MDApp.get_running_app()
        
        if not app.user_id:
            self.manager.current = 'preferences'
            return
        
        self.toolbar.title = "Updating..."
        threading.Thread(target=self.fetch_recommendations, daemon=True).start()
    
    def fetch_recommendations(self):
        """Fetch recommendations from API."""
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
                Clock.schedule_once(lambda dt: self.display_recommendations(data), 0)
            else:
                Clock.schedule_once(lambda dt: self.show_error(f"Error {response.status_code}"), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.show_error(str(e)), 0)
    
    def display_recommendations(self, data):
        """Display recommendations in beautiful cards."""
        self.toolbar.title = "Discover Montreal"
        
        # Update context
        context = data.get('context', {})
        weather = context.get('weather', 'unknown').capitalize()
        temp = context.get('temperature', 'N/A')
        period = context.get('time_period', 'N/A')
        
        app = MDApp.get_running_app()
        
        weather_emoji = {
            'sunny': '☀️', 'cloudy': '☁️', 
            'rainy': '🌧️', 'snowy': '❄️'
        }.get(context.get('weather', ''), '🌤️')
        
        self.context_label.text = (
            f"{weather_emoji} {weather} • {temp}°C\n"
            f"🕐 {period}\n"
            f"📍 {app.latitude:.4f}, {app.longitude:.4f}"
        )
        
        # Clear and add recommendations
        self.recs_container.clear_widgets()
        
        recommendations = data.get('recommendations', [])
        
        if not recommendations:
            empty_card = MDCard(
                orientation='vertical',
                padding=get_responsive_padding(),
                radius=[dp(16)],
                elevation=1,
                adaptive_height=True,
                md_bg_color=COLORS['card_bg']
            )
            empty_card.add_widget(MDLabel(
                text="No recommendations available",
                halign='center',
                font_size=get_responsive_font(16),
                theme_text_color='Hint',
                adaptive_height=True
            ))
            self.recs_container.add_widget(empty_card)
            return
        
        # Add beautiful recommendation cards
        for rec in recommendations:
            card = BeautifulRecommendationCard(
                rec_data=rec,
                on_navigate=self.on_navigate
            )
            self.recs_container.add_widget(card)
    
    def on_navigate(self, rec_data):
        """Handle navigation event."""
        logger.info(f"Navigating to: {rec_data.get('name')}")
    
    def show_error(self, error):
        """Show error message."""
        self.toolbar.title = "Discover Montreal"
        Snackbar(
            text=f"Error: {error}",
            bg_color=COLORS['error']
        ).open()
    
    def show_notifications(self):
        """Show notification history."""
        self.manager.transition.direction = 'left'
        self.manager.current = 'notifications'
    
    def go_to_settings(self):
        """Go to preferences screen."""
        self.manager.transition.direction = 'right'
        self.manager.current = 'preferences'


class NotificationScreen(MDScreen):
    """Beautiful notification history screen."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
    
    def build_ui(self):
        self.clear_widgets()
        
        layout = MDBoxLayout(orientation='vertical')
        
        # Toolbar
        self.toolbar = MDTopAppBar(
            title="Notifications",
            elevation=4,
            md_bg_color=COLORS['primary'],
            specific_text_color=(1, 1, 1, 1),
            left_action_items=[["arrow-left", lambda x: self.go_back()]],
            right_action_items=[["delete", lambda x: self.clear_all()]]
        )
        layout.add_widget(self.toolbar)
        
        # Notification list
        self.scroll = MDScrollView()
        self.list_container = MDBoxLayout(
            orientation='vertical',
            spacing=get_responsive_spacing(),
            padding=get_responsive_padding(),
            size_hint_y=None,
            md_bg_color=COLORS['background']
        )
        self.list_container.bind(minimum_height=self.list_container.setter('height'))
        
        self.scroll.add_widget(self.list_container)
        layout.add_widget(self.scroll)
        self.add_widget(layout)
    
    def on_enter(self):
        """Refresh list when entering."""
        self.refresh_list()
    
    def refresh_list(self):
        """Display notification history."""
        self.list_container.clear_widgets()
        
        main_screen = self.manager.get_screen('main')
        notifications = main_screen.notification_history
        
        if not notifications:
            self.show_empty_state()
            return
        
        # Display notifications in reverse order (newest first)
        for notif in reversed(notifications):
            self.add_notification_item(notif)
    
    def show_empty_state(self):
        """Show empty state message."""
        empty_card = MDCard(
            orientation='vertical',
            padding=get_responsive_padding() * 2,
            radius=[dp(16)],
            elevation=1,
            adaptive_height=True,
            md_bg_color=COLORS['card_bg'],
            pos_hint={'center_x': 0.5}
        )
        
        empty_card.add_widget(MDLabel(
            text="📭",
            font_size=sp(48),
            halign='center',
            size_hint_y=None,
            height=dp(60)
        ))
        
        empty_card.add_widget(MDLabel(
            text="No notifications yet",
            font_size=get_responsive_font(18),
            halign='center',
            theme_text_color='Primary',
            adaptive_height=True
        ))
        
        empty_card.add_widget(MDLabel(
            text="Your context updates will appear here",
            font_size=get_responsive_font(14),
            halign='center',
            theme_text_color='Hint',
            adaptive_height=True
        ))
        
        self.list_container.add_widget(empty_card)
    
    def add_notification_item(self, notif):
        """Add a notification item to the list."""
        notif_type = notif.get('type', 'info')
        
        # Type styling
        type_icons = {
            'location_change': '📍',
            'weather_change': '🌤️',
            'meal_time': '🍽️',
            'temperature_change': '🌡️',
            'preferences_updated': '⚙️'
        }
        
        icon = type_icons.get(notif_type, '🔔')
        
        # Parse timestamp
        try:
            ts = datetime.fromisoformat(notif['timestamp'].replace('Z', '+00:00'))
            time_str = ts.strftime("%I:%M %p • %b %d")
        except:
            time_str = ""
        
        # Create notification card
        card = MDCard(
            orientation='vertical',
            padding=get_responsive_padding(),
            spacing=dp(6),
            radius=[dp(12)],
            elevation=1,
            adaptive_height=True,
            md_bg_color=COLORS['card_bg']
        )
        
        # Header with icon and time
        header = MDBoxLayout(
            size_hint_y=None,
            height=dp(28),
            spacing=dp(8)
        )
        
        header.add_widget(MDLabel(
            text=f"{icon} {notif['title']}",
            font_size=get_responsive_font(15),
            bold=True,
            theme_text_color='Primary'
        ))
        
        header.add_widget(MDLabel(
            text=time_str,
            font_size=get_responsive_font(12),
            halign='right',
            theme_text_color='Hint',
            size_hint_x=0.4
        ))
        
        card.add_widget(header)
        
        # Message
        card.add_widget(MDLabel(
            text=notif['message'],
            font_size=get_responsive_font(13),
            theme_text_color='Secondary',
            adaptive_height=True
        ))
        
        self.list_container.add_widget(card)
    
    def clear_all(self):
        """Clear all notifications."""
        main_screen = self.manager.get_screen('main')
        main_screen.notification_history = []
        
        self.refresh_list()
        
        Snackbar(
            text="All notifications cleared",
            bg_color=COLORS['success']
        ).open()
    
    def go_back(self):
        """Return to main screen."""
        self.manager.transition.direction = 'right'
        self.manager.current = 'main'


# --- 11. Main App ---

class MontrealCompanionApp(MDApp):
    """Main application class."""
    
    user_id = StringProperty(None)
    preferences = DictProperty({})
    latitude = NumericProperty(45.5017)
    longitude = NumericProperty(-73.5673)
    
    def build(self):
        """Build the app."""
        # Set theme
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.accent_palette = "Red"
        self.theme_cls.theme_style = "Light"
        self.theme_cls.material_style = "M3"
        
        # Create screen manager
        sm = MDScreenManager()
        sm.add_widget(WelcomeScreen(name='welcome'))
        sm.add_widget(PreferencesScreen(name='preferences'))
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(NotificationScreen(name='notifications'))
        
        return sm
    
    def on_start(self):
        """Called when app starts."""
        # Request GPS permissions on Android
        if GPS_AVAILABLE:
            try:
                if platform == 'android':
                    request_permissions([Permission.ACCESS_FINE_LOCATION])
                gps.configure(on_location=self.on_gps_location)
                gps.start(minTime=10000, minDistance=10)
            except Exception as e:
                logger.warning(f"GPS initialization failed: {e}")
    
    def on_gps_location(self, **kwargs):
        """Handle GPS location updates."""
        self.latitude = kwargs.get('lat', self.latitude)
        self.longitude = kwargs.get('lon', self.longitude)
        logger.info(f"GPS Update: {self.latitude}, {self.longitude}")
    
    def on_stop(self):
        """Clean up when app stops."""
        try:
            main_screen = self.root.get_screen('main')
            if main_screen.notification_client:
                main_screen.notification_client.disconnect()
        except:
            pass


if __name__ == '__main__':
    MontrealCompanionApp().run()
