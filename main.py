"""
Montreal Travel Companion - Android App Client
ENTERPRISE PRODUCTION VERSION with Enhanced UI/UX
Professional Design System | Polished Components | Accessibility-First
"""

import os
import logging
import threading
import json
from datetime import datetime
import requests

# --- 1. Environment Configuration ---
from kivy.config import Config

Config.set('kivy', 'keyboard_mode', '')
Config.set('kivy', 'keyboard_layout', '')
Config.set('kivy', 'log_level', 'info')

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
from kivymd.uix.button import MDRaisedButton, MDRectangleFlatButton, MDIconButton, MDFillRoundFlatButton
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
from kivymd.uix.spinner import MDSpinner

from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty, DictProperty, ListProperty, BooleanProperty
from kivy.animation import Animation
from kivy.graphics import Color, Ellipse, Rectangle, Line, Triangle
from kivy.app import App

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

# Android Intents for Google Maps (only on Android)
if platform == 'android':
    try:
        from jnius import autoclass, cast
        ANDROID_INTENTS_AVAILABLE = True
    except ImportError:
        ANDROID_INTENTS_AVAILABLE = False
        logger.warning("pyjnius not available - Android intents disabled")
else:
    ANDROID_INTENTS_AVAILABLE = False

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
API_BASE_URL = "http://IP:8000"
WS_BASE_URL = "ws://IP:8000"


# ============================================================================
# DESIGN SYSTEM - Professional Color Palette & Spacing
# ============================================================================

class DesignSystem:
    """Enterprise Design System - Colors, Typography, Spacing"""
    
    # Professional Color Palette (WCAG AA Compliant) - Very Dark Jade Green
    COLORS = {
        # Primary Brand Colors - Very Dark Jade Green Theme
        'primary': (0.10, 0.45, 0.37, 1),        # Very Dark Jade #1A735F
        'primary_light': (0.18, 0.55, 0.46, 1),  # Dark Jade #2E8C75
        'primary_dark': (0.05, 0.30, 0.25, 1),   # Ultra Dark Jade #0D4D3F
        
        # Accent Colors
        'accent': (0.08, 0.40, 0.33, 1),         # Deep Dark Jade #146654
        'accent_light': (0.22, 0.60, 0.50, 1),   # Medium Jade #38997F
        
        # Semantic Colors
        'success': (0.20, 0.73, 0.45, 1),        # Green #34BA72
        'warning': (1, 0.71, 0.20, 1),           # Orange #FFB533
        'error': (0.96, 0.26, 0.31, 1),          # Red #F5424F
        'info': (0.20, 0.67, 0.94, 1),           # Cyan #33ABF0
        
        # Neutral Colors
        'background': (0.98, 0.98, 0.99, 1),     # Off-white
        'surface': (1, 1, 1, 1),                 # Pure white
        'surface_elevated': (1, 1, 1, 1),        # White with shadow
        
        # Text Colors
        'text_primary': (0.13, 0.13, 0.18, 1),   # Almost Black
        'text_secondary': (0.45, 0.47, 0.52, 1), # Gray
        'text_hint': (0.65, 0.67, 0.71, 1),      # Light Gray
        'text_disabled': (0.80, 0.81, 0.84, 1),  # Very Light Gray
        
        # Border Colors
        'border': (0.90, 0.91, 0.93, 1),         # Subtle border
        'border_focus': (0.26, 0.40, 0.96, 1),   # Focused border
        
        # Overlay
        'overlay': (0, 0, 0, 0.5),               # Semi-transparent black
        'overlay_light': (0, 0, 0, 0.08),        # Very light overlay
    }
    
    # Spacing System (8pt grid)
    SPACING = {
        'xs': dp(4),
        'sm': dp(8),
        'md': dp(16),
        'lg': dp(24),
        'xl': dp(32),
        'xxl': dp(48),
    }
    
    # Border Radius
    RADIUS = {
        'sm': dp(4),
        'md': dp(8),
        'lg': dp(12),
        'xl': dp(16),
        'round': dp(999),
    }
    
    # Elevation (shadow) - Enhanced for better depth perception
    ELEVATION = {
        'none': 0,
        'low': 2,
        'medium': 4,
        'high': 8,
        'ultra': 12,
    }
    
    # Typography Scale
    TYPOGRAPHY = {
        'h1': sp(32),
        'h2': sp(28),
        'h3': sp(24),
        'h4': sp(20),
        'h5': sp(18),
        'h6': sp(16),
        'body1': sp(16),
        'body2': sp(14),
        'caption': sp(12),
        'overline': sp(10),
    }
    
    # Touch Targets (accessibility)
    TOUCH_TARGET = {
        'min': dp(48),
        'comfortable': dp(56),
    }


DS = DesignSystem  # Shorthand


# ============================================================================
# RESPONSIVE UTILITIES
# ============================================================================

def get_responsive_value(base, breakpoints={'small': 0.85, 'large': 1.15}):
    """Calculate responsive values based on screen width"""
    width = Window.width
    if width < 360:
        return base * breakpoints.get('small', 0.85)
    elif width > 600:
        return base * breakpoints.get('large', 1.15)
    return base


# ============================================================================
# GOOGLE MAPS NAVIGATION
# ============================================================================

def open_google_maps_navigation(latitude, longitude, place_name=""):
    """
    Open Google Maps with navigation to the specified location
    Works on both Android and desktop platforms
    """
    try:
        if platform == 'android':
            # Android: Use Google Maps intent
            from jnius import autoclass, cast
            
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            Uri = autoclass('android.net.Uri')
            
            # Create navigation URI
            # Format: google.navigation:q=latitude,longitude or q=place+name
            if place_name:
                # Try with place name first (more reliable)
                uri_string = f"google.navigation:q={place_name.replace(' ', '+')}"
            else:
                # Fallback to coordinates
                uri_string = f"google.navigation:q={latitude},{longitude}"
            
            intent = Intent(Intent.ACTION_VIEW)
            intent.setData(Uri.parse(uri_string))
            intent.setPackage("com.google.android.apps.maps")
            
            current_activity = cast('android.app.Activity', PythonActivity.mActivity)
            current_activity.startActivity(intent)
            
            logger.info(f"Opened Google Maps navigation to: {place_name or f'{latitude}, {longitude}'}")
            return True
            
        else:
            # Desktop: Open Google Maps in web browser
            import webbrowser
            
            if place_name:
                # Search by place name
                url = f"https://www.google.com/maps/dir/?api=1&destination={place_name.replace(' ', '+')}"
            else:
                # Search by coordinates
                url = f"https://www.google.com/maps/dir/?api=1&destination={latitude},{longitude}"
            
            webbrowser.open(url)
            logger.info(f"Opened Google Maps in browser: {url}")
            return True
            
    except Exception as e:
        logger.error(f"Error opening Google Maps: {e}")
        return False


def open_google_maps_location(latitude, longitude, place_name=""):
    """
    Open Google Maps to view a location (without navigation)
    Alternative option for viewing the location on the map
    """
    try:
        if platform == 'android':
            from jnius import autoclass, cast
            
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            Uri = autoclass('android.net.Uri')
            
            # Format: geo:latitude,longitude?q=latitude,longitude(label)
            if place_name:
                uri_string = f"geo:{latitude},{longitude}?q={latitude},{longitude}({place_name})"
            else:
                uri_string = f"geo:{latitude},{longitude}?q={latitude},{longitude}"
            
            intent = Intent(Intent.ACTION_VIEW)
            intent.setData(Uri.parse(uri_string))
            
            current_activity = cast('android.app.Activity', PythonActivity.mActivity)
            current_activity.startActivity(intent)
            
            return True
            
        else:
            import webbrowser
            
            if place_name:
                url = f"https://www.google.com/maps/search/?api=1&query={place_name.replace(' ', '+')}"
            else:
                url = f"https://www.google.com/maps/search/?api=1&query={latitude},{longitude}"
            
            webbrowser.open(url)
            return True
            
    except Exception as e:
        logger.error(f"Error opening Google Maps location: {e}")
        return False


# ============================================================================
# ENHANCED UI COMPONENTS
# ============================================================================

class EnhancedCard(MDCard):
    """Professional Card Component with modern design"""
    
    def __init__(self, title="", show_title=True, card_style='elevated', **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.adaptive_height = True
        self.size_hint_x = 1
        self.size_hint_y = None
        self.padding = DS.SPACING['md']
        self.spacing = DS.SPACING['sm']
        self.md_bg_color = DS.COLORS['surface']
        
        # Card style variations
        if card_style == 'elevated':
            self.elevation = DS.ELEVATION['medium']
        elif card_style == 'outlined':
            self.elevation = DS.ELEVATION['none']
            self.line_color = DS.COLORS['border']
        elif card_style == 'filled':
            self.elevation = DS.ELEVATION['low']
            self.md_bg_color = DS.COLORS['background']
        
        self.bind(minimum_height=self.setter('height'))
        
        if show_title and title:
            title_label = MDLabel(
                text=title,
                font_size=DS.TYPOGRAPHY['h6'],
                theme_text_color='Custom',
                text_color=DS.COLORS['text_primary'],
                size_hint_y=None,
                height=DS.SPACING['xl'],
                halign='left',
                bold=True,
                adaptive_height=True
            )
            self.add_widget(title_label)


class PrimaryButton(MDRaisedButton):
    """Primary action button with modern style"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = DS.COLORS['primary']
        self.font_size = DS.TYPOGRAPHY['body1']
        self.size_hint_y = None
        self.height = DS.TOUCH_TARGET['comfortable']
        self.elevation = DS.ELEVATION['medium']
        
        # Add ripple effect
        self.ripple_duration_in_fast = 0.4


class SecondaryButton(MDRectangleFlatButton):
    """Secondary action button"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.line_color = DS.COLORS['primary']
        self.theme_text_color = 'Custom'
        self.text_color = DS.COLORS['primary']
        self.font_size = DS.TYPOGRAPHY['body1']
        self.size_hint_y = None
        self.height = DS.TOUCH_TARGET['comfortable']


class EnhancedTextField(MDTextField):
    """Professional text input with better styling"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mode = "rectangle"
        self.size_hint_x = 1
        self.size_hint_y = None
        self.height = DS.TOUCH_TARGET['comfortable']
        self.font_size = DS.TYPOGRAPHY['body1']
        
        # Enhanced colors
        self.line_color_normal = DS.COLORS['border']
        self.line_color_focus = DS.COLORS['primary']
        self.hint_text_color_normal = DS.COLORS['text_hint']
        self.hint_text_color_focus = DS.COLORS['primary']


class StatusChip(MDCard):
    """Status indicator chip"""
    
    def __init__(self, text="", status='info', **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint = (None, None)
        self.height = dp(32)
        self.padding = (DS.SPACING['md'], DS.SPACING['sm'])
        self.spacing = DS.SPACING['xs']
        self.elevation = DS.ELEVATION['none']
        
        # Status colors
        status_colors = {
            'success': DS.COLORS['success'],
            'warning': DS.COLORS['warning'],
            'error': DS.COLORS['error'],
            'info': DS.COLORS['info'],
            'neutral': DS.COLORS['text_secondary']
        }
        
        bg_color = status_colors.get(status, DS.COLORS['text_secondary'])
        self.md_bg_color = (*bg_color[:3], 0.15)  # 15% opacity
        
        # Status indicator dot using canvas
        dot_widget = MDWidget(
            size_hint=(None, None),
            size=(dp(8), dp(8))
        )
        
        with dot_widget.canvas:
            Color(*bg_color)
            ellipse = Ellipse(pos=dot_widget.pos, size=dot_widget.size)
        
        def update_dot(instance, value):
            ellipse.pos = instance.pos
            ellipse.size = instance.size
        
        dot_widget.bind(pos=update_dot, size=update_dot)
        
        # Text
        label = MDLabel(
            text=text,
            font_size=DS.TYPOGRAPHY['caption'],
            theme_text_color='Custom',
            text_color=bg_color,
            bold=True,
            size_hint_x=None
        )
        label.bind(texture_size=label.setter('size'))
        
        self.add_widget(dot_widget)
        self.add_widget(label)
        
        # Set width based on content
        self.bind(minimum_width=self.setter('width'))


class EnhancedNotificationBanner(MDCard):
    """Premium notification banner with smooth animations"""
    
    def __init__(self, title, message, notif_type="info", on_dismiss=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint = (0.92, None)
        self.pos_hint = {'center_x': 0.5, 'top': 1.1}  # Start off-screen
        self.elevation = DS.ELEVATION['high']
        self.on_dismiss_callback = on_dismiss
        self.height = get_responsive_value(dp(90))
        
        # Enhanced type colors - no icons, just colors
        type_styles = {
            "location_change": {
                'color': DS.COLORS['info'],
                'light_bg': (*DS.COLORS['info'][:3], 0.15)
            },
            "weather_change": {
                'color': DS.COLORS['warning'],
                'light_bg': (*DS.COLORS['warning'][:3], 0.15)
            },
            "time_period_change": {
                'color': (0.51, 0.37, 0.85, 1),
                'light_bg': (0.51, 0.37, 0.85, 0.15)
            },
            "meal_time": {
                'color': DS.COLORS['success'],
                'light_bg': (*DS.COLORS['success'][:3], 0.15)
            },
            "temperature_change": {
                'color': DS.COLORS['error'],
                'light_bg': (*DS.COLORS['error'][:3], 0.15)
            },
            "preferences_updated": {
                'color': DS.COLORS['primary'],
                'light_bg': (*DS.COLORS['primary'][:3], 0.15)
            },
            "connection_established": {
                'color': DS.COLORS['success'],
                'light_bg': (*DS.COLORS['success'][:3], 0.15)
            },
        }
        
        style = type_styles.get(notif_type, {
            'color': DS.COLORS['text_secondary'],
            'light_bg': (*DS.COLORS['text_secondary'][:3], 0.15)
        })
        
        self.md_bg_color = DS.COLORS['surface']
        
        # Left accent bar using canvas
        accent_bar = MDWidget(
            size_hint_x=None,
            width=dp(4)
        )
        
        with accent_bar.canvas:
            Color(*style['color'])
            rect = Rectangle(pos=accent_bar.pos, size=accent_bar.size)
        
        def update_bar(instance, value):
            rect.pos = instance.pos
            rect.size = instance.size
        
        accent_bar.bind(pos=update_bar, size=update_bar)
        self.add_widget(accent_bar)
        
        # Content without icon
        content = MDBoxLayout(
            orientation='horizontal',
            padding=(DS.SPACING['md'], DS.SPACING['sm']),
            spacing=DS.SPACING['md']
        )
        
        # Text content directly (no icon container)
        text_box = MDBoxLayout(orientation='vertical', spacing=dp(2))
        
        # Title with better typography
        text_box.add_widget(MDLabel(
            text=title,
            font_size=DS.TYPOGRAPHY['body1'],
            bold=True,
            theme_text_color='Custom',
            text_color=DS.COLORS['text_primary'],
            size_hint_y=None,
            height=dp(24)
        ))
        
        # Message with truncation
        max_chars = 70 if Window.width < 400 else 90
        truncated_msg = message[:max_chars] + "..." if len(message) > max_chars else message
        
        text_box.add_widget(MDLabel(
            text=truncated_msg,
            font_size=DS.TYPOGRAPHY['body2'],
            theme_text_color='Custom',
            text_color=DS.COLORS['text_secondary'],
            size_hint_y=None,
            height=dp(36)
        ))
        content.add_widget(text_box)
        
        # Close button with better styling
        close_btn = MDIconButton(
            icon="close",
            theme_text_color='Custom',
            text_color=DS.COLORS['text_hint'],
            size_hint_x=None,
            width=dp(40),
            on_release=self.dismiss
        )
        content.add_widget(close_btn)
        
        self.add_widget(content)
        
        # Animate in
        Clock.schedule_once(self.animate_in, 0.1)
    
    def animate_in(self, dt):
        """Smooth slide-in animation"""
        anim = Animation(
            pos_hint={'center_x': 0.5, 'top': 0.98},
            duration=0.4,
            transition='out_cubic'
        )
        anim.start(self)
    
    def dismiss(self, *args):
        """Smooth slide-out animation"""
        anim = Animation(
            opacity=0,
            pos_hint={'center_x': 0.5, 'top': 1.1},
            duration=0.3,
            transition='in_cubic'
        )
        anim.bind(on_complete=lambda *x: self._remove())
        anim.start(self)
    
    def _remove(self):
        if self.parent:
            self.parent.remove_widget(self)
        if self.on_dismiss_callback:
            self.on_dismiss_callback()


class LoadingOverlay(MDCard):
    """Professional loading overlay"""
    
    def __init__(self, message="Loading...", **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(200), dp(120))
        self.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
        self.md_bg_color = DS.COLORS['surface']
        self.elevation = DS.ELEVATION['high']
        self.padding = DS.SPACING['xl']
        
        layout = MDBoxLayout(
            orientation='vertical',
            spacing=DS.SPACING['md']
        )
        
        # Spinner
        spinner = MDSpinner(
            size_hint=(None, None),
            size=(dp(48), dp(48)),
            pos_hint={'center_x': 0.5},
            active=True
        )
        layout.add_widget(spinner)
        
        # Message
        layout.add_widget(MDLabel(
            text=message,
            font_size=DS.TYPOGRAPHY['body1'],
            halign='center',
            theme_text_color='Custom',
            text_color=DS.COLORS['text_secondary']
        ))
        
        self.add_widget(layout)


# ============================================================================
# NOTIFICATION CLIENT (Unchanged)
# ============================================================================

class NotificationClient:
    """WebSocket client for receiving real-time notifications from server."""
    
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
        if self._thread and self._thread.is_alive():
            logger.warning("WebSocket thread already running")
            return
        
        self._stop_flag = False
        self._thread = threading.Thread(target=self._run_websocket, daemon=True)
        self._thread.start()
        logger.info(f"WebSocket connection thread started for user {self.user_id}")
    
    def disconnect(self):
        self._stop_flag = True
        if self.ws:
            try:
                self.ws.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
        self.connected = False
        if self.on_connection_change:
            Clock.schedule_once(lambda dt: self.on_connection_change(False), 0)
    
    def _run_websocket(self):
        while not self._stop_flag and self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                ws_url = f"{WS_BASE_URL}/ws/notifications/{self.user_id}"
                logger.info(f"Connecting to WebSocket: {ws_url}")
                
                self.ws = websocket.WebSocketApp(
                    ws_url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close
                )
                
                self.ws.run_forever(ping_interval=30, ping_timeout=10)
                
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
            
            if not self._stop_flag:
                self.reconnect_attempts += 1
                logger.info(f"Reconnecting in {self.reconnect_delay}s... (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})")
                import time
                time.sleep(self.reconnect_delay)
        
        logger.info("WebSocket thread stopped")
    
    def _on_open(self, ws):
        self.connected = True
        self.reconnect_attempts = 0
        logger.info(f"WebSocket connected for user {self.user_id}")
        if self.on_connection_change:
            Clock.schedule_once(lambda dt: self.on_connection_change(True), 0)
    
    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            logger.info(f"Notification received: {data.get('type', 'unknown')}")
            Clock.schedule_once(lambda dt: self.on_notification(data), 0)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse notification: {e}")
    
    def _on_error(self, ws, error):
        logger.error(f"WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        self.connected = False
        logger.info(f"WebSocket closed: {close_status_code} - {close_msg}")
        if self.on_connection_change:
            Clock.schedule_once(lambda dt: self.on_connection_change(False), 0)


# ============================================================================
# ENHANCED SCREENS
# ============================================================================

class WelcomeScreen(MDScreen):
    """Premium welcome screen with modern design"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
    
    def build_ui(self):
        self.clear_widgets()
        
        # Root layout with gradient background
        root = MDBoxLayout(orientation='vertical')
        root.md_bg_color = DS.COLORS['primary']
        
        layout = MDBoxLayout(
            orientation='vertical',
            padding=DS.SPACING['xxl'],
            spacing=DS.SPACING['xl'],
        )
        
        # Top spacer
        layout.add_widget(MDWidget(size_hint_y=0.15))
        
        # Hero section
        hero = MDBoxLayout(
            orientation='vertical',
            spacing=DS.SPACING['md'],
            size_hint_y=None,
            height=dp(250)
        )
        
        # App icon with background - Stunning custom design
        icon_container = MDCard(
            size_hint=(None, None),
            size=(dp(140), dp(140)),
            pos_hint={'center_x': 0.5},
            md_bg_color=DS.COLORS['primary'],
            elevation=DS.ELEVATION['ultra']
        )
        
        # Create custom location/compass icon using canvas
        icon_canvas = MDWidget(size_hint=(1, 1))
        
        def draw_icon(widget, *args):
            widget.canvas.clear()
            with widget.canvas:
                # Outer glow circle
                Color(1, 1, 1, 0.25)
                Ellipse(
                    pos=(widget.x + dp(20), widget.y + dp(20)),
                    size=(dp(100), dp(100))
                )
                
                # Main white circle
                Color(1, 1, 1, 1)
                Ellipse(
                    pos=(widget.x + dp(40), widget.y + dp(40)),
                    size=(dp(60), dp(60))
                )
                
                # Location pin shape
                Color(*DS.COLORS['primary_dark'])
                # Draw teardrop shape using lines
                from kivy.graphics import Line
                center_x = widget.x + dp(70)
                center_y = widget.y + dp(70)
                
                # Pin circle
                Ellipse(
                    pos=(center_x - dp(12), center_y + dp(5)),
                    size=(dp(24), dp(24))
                )
                
                # Pin point (triangle)
                from kivy.graphics import Triangle
                Triangle(
                    points=[
                        center_x, center_y - dp(15),      # Bottom point
                        center_x - dp(10), center_y + dp(5),  # Left
                        center_x + dp(10), center_y + dp(5),  # Right
                    ]
                )
                
                # Center dot
                Color(1, 1, 1, 1)
                Ellipse(
                    pos=(center_x - dp(5), center_y + dp(10)),
                    size=(dp(10), dp(10))
                )
        
        icon_canvas.bind(pos=draw_icon, size=draw_icon)
        Clock.schedule_once(lambda dt: draw_icon(icon_canvas), 0)
        
        icon_container.add_widget(icon_canvas)
        hero.add_widget(icon_container)
        
        # App title with better typography
        hero.add_widget(MDLabel(
            text='Montreal\nTravel Companion',
            font_size=get_responsive_value(DS.TYPOGRAPHY['h1']),
            bold=True,
            halign='center',
            theme_text_color='Custom',
            text_color=DS.COLORS['surface'],
            size_hint_y=None,
            height=dp(90)
        ))
        
        # Subtitle
        hero.add_widget(MDLabel(
            text='Your AI-powered travel guide',
            font_size=DS.TYPOGRAPHY['h6'],
            halign='center',
            theme_text_color='Custom',
            text_color=(*DS.COLORS['surface'][:3], 0.8),
            size_hint_y=None,
            height=dp(30)
        ))
        
        layout.add_widget(hero)
        
        # Features section
        features = MDBoxLayout(
            orientation='vertical',
            spacing=DS.SPACING['sm'],
            size_hint_y=None,
            height=dp(120)
        )
        
        feature_items = [
            "• Personalized Recommendations",
            "• Weather-Aware Suggestions",
            "• Real-Time Location Tracking"
        ]
        
        for feature in feature_items:
            features.add_widget(MDLabel(
                text=feature,
                font_size=DS.TYPOGRAPHY['body1'],
                halign='center',
                theme_text_color='Custom',
                text_color=(*DS.COLORS['surface'][:3], 0.9),
                size_hint_y=None,
                height=dp(32)
            ))
        
        layout.add_widget(features)
        
        # Spacer
        layout.add_widget(MDWidget(size_hint_y=0.1))
        
        # CTA Button with enhanced styling
        btn_container = MDBoxLayout(
            size_hint_y=None,
            height=DS.TOUCH_TARGET['comfortable'] + DS.SPACING['md'],
            padding=(DS.SPACING['lg'], 0)
        )
        
        btn = MDRaisedButton(
            text='GET STARTED',
            font_size=DS.TYPOGRAPHY['h6'],
            size_hint_x=1,
            size_hint_y=None,
            height=DS.TOUCH_TARGET['comfortable'],
            elevation=DS.ELEVATION['high'],
            md_bg_color=DS.COLORS['primary'],
            on_release=self.go_to_preferences
        )
        btn_container.add_widget(btn)
        layout.add_widget(btn_container)
        
        # Bottom spacer
        layout.add_widget(MDWidget(size_hint_y=0.1))
        
        root.add_widget(layout)
        self.add_widget(root)
    
    def go_to_preferences(self, instance):
        self.manager.transition.direction = 'left'
        self.manager.current = 'preferences'


class PreferencesScreen(MDScreen):
    """Enhanced preferences screen with better UX"""
    activity_type = StringProperty("outdoor")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
    
    def build_ui(self):
        self.clear_widgets()
        
        layout = MDBoxLayout(orientation='vertical')
        
        # Enhanced toolbar
        self.toolbar = MDTopAppBar(
            title="Your Preferences",
            elevation=0,
            md_bg_color=DS.COLORS['surface'],
            specific_text_color=DS.COLORS['text_primary'],
            left_action_items=[["arrow-left", lambda x: self.go_back()]]
        )
        layout.add_widget(self.toolbar)
        
        # Progress indicator
        progress_bar = MDBoxLayout(
            size_hint_y=None,
            height=dp(3),
            md_bg_color=DS.COLORS['background']
        )
        progress_fill = MDWidget(
            size_hint=(0.5, 1),
            md_bg_color=DS.COLORS['primary']
        )
        progress_bar.add_widget(progress_fill)
        progress_bar.add_widget(MDWidget(size_hint=(0.5, 1)))
        layout.add_widget(progress_bar)
        
        # Scrollable content
        scroll = MDScrollView()
        content = MDBoxLayout(
            orientation='vertical',
            spacing=DS.SPACING['lg'],
            padding=DS.SPACING['md'],
            size_hint_y=None
        )
        content.bind(minimum_height=content.setter('height'))
        
        # Helper text
        content.add_widget(MDLabel(
            text="Tell us about your preferences",
            font_size=DS.TYPOGRAPHY['body2'],
            theme_text_color='Custom',
            text_color=DS.COLORS['text_secondary'],
            size_hint_y=None,
            height=dp(30)
        ))
        
        # 1. Profile Card
        card_profile = EnhancedCard(title="Profile", card_style='elevated')
        self.user_id_input = EnhancedTextField(
            hint_text="Enter your username",
            text="traveler1",
            helper_text="This will be your unique identifier",
            helper_text_mode="on_focus"
        )
        card_profile.add_widget(self.user_id_input)
        content.add_widget(card_profile)
        
        # 2. Meal Times Card
        card_meals = EnhancedCard(title="Dining Schedule", card_style='elevated')
        
        card_meals.add_widget(MDLabel(
            text="When do you prefer to eat?",
            font_size=DS.TYPOGRAPHY['body2'],
            theme_text_color='Custom',
            text_color=DS.COLORS['text_secondary'],
            size_hint_y=None,
            height=dp(24)
        ))
        
        meals_grid = MDGridLayout(
            cols=1 if Window.width < 400 else 3,
            spacing=DS.SPACING['md'],
            size_hint_y=None,
            adaptive_height=True
        )
        meals_grid.bind(minimum_height=meals_grid.setter('height'))
        
        self.input_breakfast = EnhancedTextField(
            text="08:00",
            hint_text="Breakfast Time",
            helper_text="HH:MM format"
        )
        self.input_lunch = EnhancedTextField(
            text="12:00",
            hint_text="Lunch Time",
            helper_text="HH:MM format"
        )
        self.input_dinner = EnhancedTextField(
            text="19:00",
            hint_text="Dinner Time",
            helper_text="HH:MM format"
        )
        
        meals_grid.add_widget(self.input_breakfast)
        meals_grid.add_widget(self.input_lunch)
        meals_grid.add_widget(self.input_dinner)
        
        card_meals.add_widget(meals_grid)
        content.add_widget(card_meals)
        
        # 3. Activity Type Card
        card_activity = EnhancedCard(title="Activity Preference", card_style='elevated')
        
        card_activity.add_widget(MDLabel(
            text="What's your preferred activity style?",
            font_size=DS.TYPOGRAPHY['body2'],
            theme_text_color='Custom',
            text_color=DS.COLORS['text_secondary'],
            size_hint_y=None,
            height=dp(24)
        ))
        
        btn_box = MDBoxLayout(
            spacing=DS.SPACING['md'],
            size_hint_y=None,
            height=DS.TOUCH_TARGET['comfortable']
        )
        
        self.btn_indoor = MDFillRoundFlatButton(
            text="Indoor",
            size_hint_x=0.5,
            font_size=DS.TYPOGRAPHY['body1'],
            on_release=lambda x: self.set_activity("indoor")
        )
        self.btn_outdoor = MDFillRoundFlatButton(
            text="Outdoor",
            size_hint_x=0.5,
            font_size=DS.TYPOGRAPHY['body1'],
            md_bg_color=DS.COLORS['primary'],
            on_release=lambda x: self.set_activity("outdoor")
        )
        
        btn_box.add_widget(self.btn_indoor)
        btn_box.add_widget(self.btn_outdoor)
        card_activity.add_widget(btn_box)
        content.add_widget(card_activity)
        
        # 4. Cuisines Card
        card_cuisines = EnhancedCard(title="Cuisine Preferences", card_style='elevated')
        
        card_cuisines.add_widget(MDLabel(
            text="Select your favorite cuisines",
            font_size=DS.TYPOGRAPHY['body2'],
            theme_text_color='Custom',
            text_color=DS.COLORS['text_secondary'],
            size_hint_y=None,
            height=dp(24)
        ))
        
        self.cuisines = ['Italian', 'French', 'Japanese', 'Mexican', 'Burgers', 'Cafe', 'Seafood']
        self.cuisine_checks = {}
        
        cuisine_grid = MDGridLayout(
            cols=1 if Window.width < 360 else 2,
            spacing=DS.SPACING['sm'],
            size_hint_y=None,
            adaptive_height=True
        )
        cuisine_grid.bind(minimum_height=cuisine_grid.setter('height'))
        
        cuisine_emojis = {
            'Italian': '', 'French': '', 'Japanese': '',
            'Mexican': '', 'Burgers': '', 'Cafe': '', 'Seafood': ''
        }
        
        for cuisine in self.cuisines:
            row = MDCard(
                orientation='horizontal',
                size_hint_y=None,
                height=dp(56),
                padding=(DS.SPACING['md'], DS.SPACING['sm']),
                spacing=DS.SPACING['md'],
                md_bg_color=DS.COLORS['background'],
                elevation=DS.ELEVATION['none']
            )
            
            chk = MDCheckbox(
                size_hint=(None, None),
                size=(dp(48), dp(48)),
                active=(cuisine == 'French')
            )
            self.cuisine_checks[cuisine] = chk
            row.add_widget(chk)
            
            row.add_widget(MDLabel(
                text=f"{cuisine}",
                theme_text_color="Custom",
                text_color=DS.COLORS['text_primary'],
                font_size=DS.TYPOGRAPHY['body1']
            ))
            
            cuisine_grid.add_widget(row)
        
        card_cuisines.add_widget(cuisine_grid)
        content.add_widget(card_cuisines)
        
        # Save Button
        btn_container = MDBoxLayout(
            size_hint_y=None,
            height=DS.TOUCH_TARGET['comfortable'] + DS.SPACING['md'],
            padding=(DS.SPACING['md'], DS.SPACING['md'])
        )
        
        save_btn = PrimaryButton(
            text="CONTINUE",
            size_hint_x=1,
            on_release=self.save_prefs_thread
        )
        save_btn.md_bg_color = DS.COLORS['success']
        btn_container.add_widget(save_btn)
        content.add_widget(btn_container)
        
        # Bottom padding
        content.add_widget(MDWidget(size_hint_y=None, height=DS.SPACING['xl']))
        
        scroll.add_widget(content)
        layout.add_widget(scroll)
        self.add_widget(layout)
    
    def set_activity(self, mode):
        self.activity_type = mode
        if mode == "indoor":
            self.btn_indoor.md_bg_color = DS.COLORS['primary']
            self.btn_indoor.text_color = DS.COLORS['surface']
            self.btn_outdoor.md_bg_color = DS.COLORS['background']
            self.btn_outdoor.text_color = DS.COLORS['primary']
        else:
            self.btn_outdoor.md_bg_color = DS.COLORS['primary']
            self.btn_outdoor.text_color = DS.COLORS['surface']
            self.btn_indoor.md_bg_color = DS.COLORS['background']
            self.btn_indoor.text_color = DS.COLORS['primary']
    
    def go_back(self):
        self.manager.transition.direction = 'right'
        self.manager.current = 'welcome'
    
    def save_prefs_thread(self, instance):
        if not self.user_id_input.text.strip():
            self.show_error_dialog("Please enter a username")
            return
        
        self.show_loading()
        threading.Thread(target=self.save_prefs_api, daemon=True).start()
    
    def save_prefs_api(self):
        user_id = self.user_id_input.text.strip()
        
        meal_times = {
            "breakfast": self.input_breakfast.text.strip(),
            "lunch": self.input_lunch.text.strip(),
            "dinner": self.input_dinner.text.strip()
        }
        
        payload = {
            "user_id": user_id,
            "activity_type": self.activity_type,
            "preferred_cuisines": [k for k, v in self.cuisine_checks.items() if v.active],
            "meal_times": meal_times
        }
        
        app = App.get_running_app()
        app.user_id = user_id
        app.preferences = payload
        
        try:
            response = requests.post(f"{API_BASE_URL}/api/preferences", json=payload, timeout=5)
            if response.status_code == 200:
                Clock.schedule_once(self.on_save_success, 0)
            else:
                Clock.schedule_once(lambda dt: self.on_save_error(f"Server Error: {response.status_code}"), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.on_save_error(str(e)), 0)
    
    def show_loading(self):
        overlay = LoadingOverlay(message="Saving preferences...")
        
        # Dim background
        self.loading_bg = MDWidget(
            size_hint=(1, 1),
            md_bg_color=DS.COLORS['overlay']
        )
        self.add_widget(self.loading_bg)
        self.add_widget(overlay)
        self.loading_overlay = overlay
    
    def hide_loading(self):
        if hasattr(self, 'loading_overlay'):
            self.remove_widget(self.loading_overlay)
            self.remove_widget(self.loading_bg)
    
    def on_save_success(self, dt):
        self.hide_loading()
        self.manager.transition.direction = 'left'
        self.manager.current = 'main'
    
    def on_save_error(self, error_msg):
        self.hide_loading()
        self.show_error_dialog(
            f"Could not save preferences.\n\n{error_msg}\n\nPlease ensure the server is running."
        )
    
    def show_error_dialog(self, message):
        dialog = MDDialog(
            title="Error",
            text=message,
            buttons=[
                SecondaryButton(
                    text="OK",
                    on_release=lambda x: dialog.dismiss()
                )
            ]
        )
        dialog.open()


class MainScreen(MDScreen):
    """Premium dashboard with enhanced visuals"""
    
    notification_count = NumericProperty(0)
    ws_connected = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.notification_client = None
        self.current_banner = None
        self.notification_history = []
        self.build_ui()
    
    def build_ui(self):
        self.clear_widgets()
        
        layout = MDBoxLayout(orientation='vertical')
        
        # Enhanced toolbar with elevation
        self.toolbar = MDTopAppBar(
            title="Explore Montreal",
            elevation=0,
            md_bg_color=DS.COLORS['primary'],
            specific_text_color=DS.COLORS['surface'],
            right_action_items=[
                ["refresh", lambda x: self.refresh_data()],
                ["bell-outline", lambda x: self.show_notification_history()],
                ["cog", lambda x: self.go_to_settings()]
            ]
        )
        layout.add_widget(self.toolbar)
        
        # Enhanced status bar
        self.status_bar = MDCard(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(36),
            md_bg_color=(*DS.COLORS['error'][:3], 0.1),
            padding=(DS.SPACING['md'], DS.SPACING['sm']),
            spacing=DS.SPACING['sm'],
            elevation=DS.ELEVATION['none']
        )
        
        status_dot = MDWidget(
            size_hint=(None, None),
            size=(dp(10), dp(10))
        )
        # Add colored circle using canvas
        with status_dot.canvas:
            status_dot.color_instruction = Color(*DS.COLORS['error'])
            status_dot.ellipse = Ellipse(
                pos=status_dot.pos,
                size=status_dot.size
            )
        
        # Update ellipse position when widget moves
        def update_ellipse(instance, value):
            status_dot.ellipse.pos = instance.pos
            status_dot.ellipse.size = instance.size
        
        status_dot.bind(pos=update_ellipse, size=update_ellipse)
        self.status_dot = status_dot
        
        self.status_label = MDLabel(
            text="Disconnected",
            font_size=DS.TYPOGRAPHY['caption'],
            theme_text_color="Custom",
            text_color=DS.COLORS['error'],
            bold=True
        )
        
        self.status_bar.add_widget(status_dot)
        self.status_bar.add_widget(self.status_label)
        layout.add_widget(self.status_bar)
        
        # Scrollable content
        self.scroll = MDScrollView()
        self.content = MDBoxLayout(
            orientation='vertical',
            spacing=DS.SPACING['lg'],
            padding=DS.SPACING['md'],
            size_hint_y=None
        )
        self.content.bind(minimum_height=self.content.setter('height'))
        
        # Context Card with enhanced styling
        self.context_card = EnhancedCard(title="Current Context", card_style='elevated')
        
        # Context content box with better layout
        context_content = MDBoxLayout(
            orientation='vertical',
            spacing=DS.SPACING['sm'],
            size_hint_y=None,
            height=dp(90),
            padding=(DS.SPACING['sm'], 0)
        )
        
        # Weather row - no icon, just clean text
        self.weather_row = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(32),
            spacing=DS.SPACING['sm']
        )
        self.weather_text = MDLabel(
            text="Loading weather...",
            font_size=DS.TYPOGRAPHY['body1'],
            theme_text_color='Custom',
            text_color=DS.COLORS['text_primary'],
            bold=True,
            valign='center'
        )
        self.weather_row.add_widget(self.weather_text)
        context_content.add_widget(self.weather_row)
        
        # Time row - no icon, clean text
        self.time_row = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(28),
            spacing=DS.SPACING['sm']
        )
        self.time_text = MDLabel(
            text="Loading time...",
            font_size=DS.TYPOGRAPHY['body2'],
            theme_text_color='Custom',
            text_color=DS.COLORS['text_secondary'],
            valign='center'
        )
        self.time_row.add_widget(self.time_text)
        context_content.add_widget(self.time_row)
        
        # Location row - no icon, clean text
        self.location_row = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(28),
            spacing=DS.SPACING['sm']
        )
        self.location_text = MDLabel(
            text="Loading location...",
            font_size=DS.TYPOGRAPHY['caption'],
            theme_text_color='Custom',
            text_color=DS.COLORS['text_hint'],
            valign='center'
        )
        self.location_row.add_widget(self.location_text)
        context_content.add_widget(self.location_row)
        
        self.context_card.add_widget(context_content)
        self.content.add_widget(self.context_card)
        
        # Section header
        header_box = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(40),
            spacing=DS.SPACING['sm']
        )
        header_box.add_widget(MDLabel(
            text="Recommended for You",
            font_size=DS.TYPOGRAPHY['h5'],
            bold=True,
            theme_text_color='Custom',
            text_color=DS.COLORS['text_primary']
        ))
        self.content.add_widget(header_box)
        
        # Recommendations container
        self.recs_box = MDBoxLayout(
            orientation='vertical',
            spacing=DS.SPACING['md'],
            size_hint_y=None
        )
        self.recs_box.bind(minimum_height=self.recs_box.setter('height'))
        self.content.add_widget(self.recs_box)
        
        self.scroll.add_widget(self.content)
        layout.add_widget(self.scroll)
        self.add_widget(layout)
    
    def on_enter(self):
        app = App.get_running_app()
        
        if app.user_id and WEBSOCKET_AVAILABLE:
            self.start_notification_client()
        
        self.context_update_event = Clock.schedule_interval(self.send_context_update, 60)
        self.refresh_data()
    
    def on_leave(self):
        if hasattr(self, 'context_update_event'):
            self.context_update_event.cancel()
    
    def start_notification_client(self):
        app = App.get_running_app()
        
        if self.notification_client:
            self.notification_client.disconnect()
        
        if not WEBSOCKET_AVAILABLE:
            logger.warning("WebSocket not available")
            return
        
        self.notification_client = NotificationClient(
            user_id=app.user_id,
            on_notification_callback=self.handle_notification,
            on_connection_change_callback=self.on_ws_connection_change
        )
        self.notification_client.connect()
    
    def on_ws_connection_change(self, connected):
        self.ws_connected = connected
        if connected:
            self.status_label.text = "Connected - Live Updates"
            self.status_label.text_color = DS.COLORS['success']
            self.status_dot.color_instruction.rgba = DS.COLORS['success']
            self.status_bar.md_bg_color = (*DS.COLORS['success'][:3], 0.1)
        else:
            self.status_label.text = "Disconnected"
            self.status_label.text_color = DS.COLORS['error']
            self.status_dot.color_instruction.rgba = DS.COLORS['error']
            self.status_bar.md_bg_color = (*DS.COLORS['error'][:3], 0.1)
    
    def handle_notification(self, notification):
        notif_type = notification.get('type', 'info')
        title = notification.get('title', 'Notification')
        message = notification.get('message', '')
        
        logger.info(f"Handling notification: {title}")
        
        self.notification_history.append({
            'type': notif_type,
            'title': title,
            'message': message,
            'timestamp': notification.get('timestamp', datetime.now().isoformat())
        })
        
        if len(self.notification_history) > 50:
            self.notification_history = self.notification_history[-50:]
        
        self.notification_count = len(self.notification_history)
        self.update_bell_icon()
        
        if notif_type not in ['connection_established', 'pong']:
            self.show_notification_banner(title, message, notif_type)
            
            if notif_type in ['location_change', 'weather_change', 'preferences_updated', 'meal_time']:
                Clock.schedule_once(lambda dt: self.refresh_data(), 1)
    
    def show_notification_banner(self, title, message, notif_type="info"):
        if self.current_banner and self.current_banner.parent:
            self.current_banner.parent.remove_widget(self.current_banner)
        
        self.current_banner = EnhancedNotificationBanner(
            title=title,
            message=message,
            notif_type=notif_type,
            on_dismiss=lambda: setattr(self, 'current_banner', None)
        )
        
        self.add_widget(self.current_banner)
        Clock.schedule_once(lambda dt: self.current_banner.dismiss() if self.current_banner else None, 6)
    
    def update_bell_icon(self):
        if self.notification_count > 0:
            self.toolbar.right_action_items[1] = ["bell", lambda x: self.show_notification_history()]
        else:
            self.toolbar.right_action_items[1] = ["bell-outline", lambda x: self.show_notification_history()]
    
    def send_context_update(self, dt=None):
        app = App.get_running_app()
        
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
                    logger.info(f"Context updated: {data.get('notifications_generated', 0)} notifications")
                    
            except Exception as e:
                logger.error(f"Context update failed: {e}")
        
        threading.Thread(target=_send, daemon=True).start()
    
    def go_to_settings(self):
        self.manager.transition.direction = 'right'
        self.manager.current = 'preferences'
    
    def refresh_data(self):
        app = App.get_running_app()
        
        if not app.user_id:
            self.manager.current = 'preferences'
            return
        
        # Show loading state
        self.show_loading_state()
        threading.Thread(target=self.fetch_api_data, daemon=True).start()
    
    def show_loading_state(self):
        """Show loading skeleton"""
        self.weather_text.text = "Loading weather..."
        self.time_text.text = "Loading time..."
        self.location_text.text = "Loading location..."
        self.recs_box.clear_widgets()
        
        # Add skeleton cards
        for i in range(3):
            skeleton = EnhancedCard(show_title=False, card_style='filled')
            skeleton.add_widget(MDWidget(size_hint_y=None, height=dp(100)))
            self.recs_box.add_widget(skeleton)
    
    def fetch_api_data(self):
        app = App.get_running_app()
        
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
                err_msg = f"Server returned error {response.status_code}"
                Clock.schedule_once(lambda dt: self.show_error(err_msg), 0)
                
        except requests.exceptions.ConnectionError:
            Clock.schedule_once(lambda dt: self.show_error("Cannot connect to server"), 0)
    
    def update_ui(self, data):
        app = App.get_running_app()
        
        context = data.get("context", {})
        recs = data.get("recommendations", [])
        
        weather = context.get("weather", "Unknown").capitalize()
        temp = context.get("temperature", "N/A")
        period = context.get("time_period", "N/A")
        
        # Update context card fields - clean text without icons
        self.weather_text.text = f"{weather} • {temp}°C"
        self.time_text.text = period
        self.location_text.text = f"{app.latitude:.4f}, {app.longitude:.4f}"
        
        self.recs_box.clear_widgets()
        
        if not recs:
            empty_state = EnhancedCard(show_title=False, card_style='outlined')
            empty_box = MDBoxLayout(
                orientation='vertical',
                spacing=DS.SPACING['md'],
                padding=DS.SPACING['lg']
            )
            empty_box.add_widget(MDLabel(
                text="🔍",
                font_size=sp(48),
                halign='center',
                size_hint_y=None,
                height=dp(60)
            ))
            empty_box.add_widget(MDLabel(
                text="No recommendations found",
                font_size=DS.TYPOGRAPHY['h6'],
                halign='center',
                theme_text_color='Custom',
                text_color=DS.COLORS['text_primary'],
                bold=True,
                size_hint_y=None,
                height=dp(30)
            ))
            empty_box.add_widget(MDLabel(
                text="Try adjusting your preferences or location",
                font_size=DS.TYPOGRAPHY['body2'],
                halign='center',
                theme_text_color='Custom',
                text_color=DS.COLORS['text_secondary'],
                size_hint_y=None,
                height=dp(40)
            ))
            empty_state.add_widget(empty_box)
            self.recs_box.add_widget(empty_state)
            return
        
        for rec in recs:
            card = self.create_recommendation_card(rec)
            self.recs_box.add_widget(card)
    
    def create_recommendation_card(self, rec):
        """Create premium recommendation card with enhanced visual design"""
        card = EnhancedCard(show_title=False, card_style='elevated')
        
        # Main content container
        content = MDBoxLayout(
            orientation='vertical',
            spacing=DS.SPACING['sm'],
            size_hint_y=None,
            height=dp(140)
        )
        
        # Header with name and rating badge
        header = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(32),
            spacing=DS.SPACING['sm']
        )
        
        name = rec.get('name', 'Unknown')
        max_name_len = 28 if Window.width < 400 else 38
        if len(name) > max_name_len:
            name = name[:max_name_len] + "..."
        
        header.add_widget(MDLabel(
            text=name,
            font_size=DS.TYPOGRAPHY['h6'],
            bold=True,
            theme_text_color='Custom',
            text_color=DS.COLORS['text_primary'],
            shorten=True,
            shorten_from='right'
        ))
        
        # Rating badge with yellow background
        if rec.get('rating'):
            rating_card = MDCard(
                size_hint=(None, None),
                size=(dp(65), dp(28)),
                md_bg_color=(1, 0.95, 0.8, 1),  # Light yellow
                elevation=DS.ELEVATION['none'],
                padding=(DS.SPACING['sm'], 0)
            )
            rating_label = MDLabel(
                text=f"★ {rec['rating']}",
                font_size=DS.TYPOGRAPHY['caption'],
                bold=True,
                halign='center',
                valign='center',
                theme_text_color='Custom',
                text_color=(0.8, 0.6, 0, 1)  # Gold color
            )
            rating_card.add_widget(rating_label)
            header.add_widget(rating_card)
        
        content.add_widget(header)
        
        # Type/Category - clean text without icon
        type_row = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(22),
            spacing=DS.SPACING['xs']
        )
        
        desc = rec.get('description', '') or rec.get('type', '')
        max_desc_len = 40 if Window.width < 400 else 50
        if len(desc) > max_desc_len:
            desc = desc[:max_desc_len] + "..."
        
        type_row.add_widget(MDLabel(
            text=desc,
            font_size=DS.TYPOGRAPHY['body2'],
            theme_text_color='Custom',
            text_color=DS.COLORS['text_secondary']
        ))
        content.add_widget(type_row)
        
        # Reason with enhanced styling - no icon in badge
        reason = rec.get('reason', '')
        max_reason_len = 55 if Window.width < 400 else 75
        if len(reason) > max_reason_len:
            reason = reason[:max_reason_len] + "..."
        
        reason_card = MDCard(
            size_hint_y=None,
            height=dp(32),
            md_bg_color=(*DS.COLORS['primary'][:3], 0.08),
            elevation=DS.ELEVATION['none'],
            padding=(DS.SPACING['sm'], DS.SPACING['xs'])
        )
        reason_label = MDLabel(
            text=reason,
            font_size=DS.TYPOGRAPHY['caption'],
            theme_text_color='Custom',
            text_color=DS.COLORS['primary'],
            italic=True,
            valign='center'
        )
        reason_card.add_widget(reason_label)
        content.add_widget(reason_card)
        
        # Footer with distance and navigate button
        footer = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(44),
            spacing=DS.SPACING['md']
        )
        
        # Distance - clean text without icon
        dist = rec.get('distance', 0)
        if dist > 1000:
            dist_str = f"{dist/1000:.1f} km away"
        else:
            dist_str = f"{dist} m away"
        
        distance_box = MDBoxLayout(
            orientation='horizontal',
            spacing=DS.SPACING['xs']
        )
        distance_box.add_widget(MDLabel(
            text=dist_str,
            font_size=DS.TYPOGRAPHY['caption'],
            theme_text_color='Custom',
            text_color=DS.COLORS['text_hint'],
            valign='center'
        ))
        footer.add_widget(distance_box)
        
        # Enhanced NAVIGATE button with dark jade green
        nav_btn = MDRaisedButton(
            text="NAVIGATE",
            size_hint_x=None,
            width=dp(120),
            height=dp(40),
            md_bg_color=DS.COLORS['primary'],
            font_size=DS.TYPOGRAPHY['body2'],
            elevation=DS.ELEVATION['medium'],
            on_release=lambda x: self.navigate_to_place(rec)
        )
        footer.add_widget(nav_btn)
        
        content.add_widget(footer)
        card.add_widget(content)
        
        return card
    
    def show_error(self, msg):
        Snackbar(
            text=f"Error: {msg}",
            snackbar_x="10dp",
            snackbar_y="10dp",
            size_hint_x=.9,
            bg_color=DS.COLORS['error']
        ).open()
    
    def navigate_to_place(self, recommendation):
        """Open Google Maps navigation to the recommended place"""
        try:
            latitude = recommendation.get('latitude')
            longitude = recommendation.get('longitude')
            name = recommendation.get('name', '')
            
            if latitude and longitude:
                # Try to open navigation
                success = open_google_maps_navigation(latitude, longitude, name)
                
                if success:
                    Snackbar(
                        text=f"Opening navigation to {name}...",
                        snackbar_x="10dp",
                        snackbar_y="10dp",
                        size_hint_x=.9,
                        bg_color=DS.COLORS['success'],
                        duration=2
                    ).open()
                else:
                    # Fallback: try just viewing location
                    success = open_google_maps_location(latitude, longitude, name)
                    if success:
                        Snackbar(
                            text=f"Opening {name} in Maps...",
                            snackbar_x="10dp",
                            snackbar_y="10dp",
                            size_hint_x=.9,
                            bg_color=DS.COLORS['info'],
                            duration=2
                        ).open()
                    else:
                        raise Exception("Could not open maps")
            else:
                Snackbar(
                    text="Location coordinates not available",
                    snackbar_x="10dp",
                    snackbar_y="10dp",
                    size_hint_x=.9,
                    bg_color=DS.COLORS['warning']
                ).open()
                
        except Exception as e:
            logger.error(f"Navigation error: {e}")
            Snackbar(
                text="Could not open Google Maps",
                snackbar_x="10dp",
                snackbar_y="10dp",
                size_hint_x=.9,
                bg_color=DS.COLORS['error']
            ).open()
    
    def show_notification_history(self):
        self.manager.transition.direction = 'left'
        self.manager.current = 'notifications'


class NotificationHistoryScreen(MDScreen):
    """Enhanced notification history screen"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
    
    def build_ui(self):
        self.clear_widgets()
        
        layout = MDBoxLayout(orientation='vertical')
        
        # Toolbar
        self.toolbar = MDTopAppBar(
            title="Notifications",
            elevation=0,
            md_bg_color=DS.COLORS['surface'],
            specific_text_color=DS.COLORS['text_primary'],
            left_action_items=[["arrow-left", lambda x: self.go_back()]],
            right_action_items=[["delete", lambda x: self.clear_notifications()]]
        )
        layout.add_widget(self.toolbar)
        
        # Notification list
        self.scroll = MDScrollView()
        self.list_container = MDBoxLayout(
            orientation='vertical',
            spacing=DS.SPACING['md'],
            padding=DS.SPACING['md'],
            size_hint_y=None
        )
        self.list_container.bind(minimum_height=self.list_container.setter('height'))
        self.scroll.add_widget(self.list_container)
        layout.add_widget(self.scroll)
        
        self.add_widget(layout)
    
    def on_enter(self):
        self.refresh_list()
    
    def refresh_list(self):
        self.list_container.clear_widgets()
        
        main_screen = self.manager.get_screen('main')
        notifications = main_screen.notification_history
        
        if not notifications:
            # Enhanced empty state
            empty_state = EnhancedCard(show_title=False, card_style='outlined')
            empty_box = MDBoxLayout(
                orientation='vertical',
                spacing=DS.SPACING['md'],
                padding=DS.SPACING['xxl']
            )
            empty_box.add_widget(MDLabel(
                text="📭",
                font_size=sp(60),
                halign='center',
                size_hint_y=None,
                height=dp(80)
            ))
            empty_box.add_widget(MDLabel(
                text="No notifications yet",
                font_size=DS.TYPOGRAPHY['h5'],
                halign='center',
                theme_text_color='Custom',
                text_color=DS.COLORS['text_primary'],
                bold=True,
                size_hint_y=None,
                height=dp(36)
            ))
            empty_box.add_widget(MDLabel(
                text="Context changes will appear here",
                font_size=DS.TYPOGRAPHY['body2'],
                halign='center',
                theme_text_color='Custom',
                text_color=DS.COLORS['text_secondary'],
                size_hint_y=None,
                height=dp(30)
            ))
            empty_state.add_widget(empty_box)
            self.list_container.add_widget(empty_state)
            return
        
        # Color mapping only (no icons)
        color_map = {
            "location_change": DS.COLORS['info'],
            "weather_change": DS.COLORS['warning'],
            "time_period_change": (0.51, 0.37, 0.85, 1),
            "meal_time": DS.COLORS['success'],
            "temperature_change": DS.COLORS['error'],
            "preferences_updated": DS.COLORS['primary'],
            "connection_established": DS.COLORS['success'],
        }
        
        for notif in reversed(notifications):
            notif_type = notif.get('type', 'info')
            color = color_map.get(notif_type, DS.COLORS['text_secondary'])
            
            try:
                ts = datetime.fromisoformat(notif['timestamp'].replace('Z', '+00:00'))
                time_str = ts.strftime("%I:%M %p • %b %d")
            except:
                time_str = ""
            
            # Enhanced notification card
            card = EnhancedCard(show_title=False, card_style='elevated')
            
            # Header
            header = MDBoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                height=dp(28),
                spacing=DS.SPACING['sm']
            )
            
            # Colored dot indicator (no icon)
            dot_widget = MDWidget(
                size_hint=(None, None),
                size=(dp(12), dp(12))
            )
            with dot_widget.canvas:
                Color(*color)
                dot = Ellipse(pos=dot_widget.pos, size=dot_widget.size)
            
            def update_dot(instance, value, dot_ref=dot):
                dot_ref.pos = instance.pos
                dot_ref.size = instance.size
            
            dot_widget.bind(pos=update_dot, size=update_dot)
            
            # Wrapper for centering the dot
            dot_container = MDBoxLayout(
                orientation='horizontal',
                size_hint=(None, None),
                size=(dp(28), dp(28))
            )
            dot_container.add_widget(MDWidget(size_hint_x=None, width=dp(8)))
            dot_container.add_widget(dot_widget)
            header.add_widget(dot_container)
            
            # Title and time
            title_box = MDBoxLayout(orientation='vertical', spacing=dp(2))
            title_box.add_widget(MDLabel(
                text=notif['title'],
                font_size=DS.TYPOGRAPHY['body1'],
                bold=True,
                theme_text_color='Custom',
                text_color=DS.COLORS['text_primary']
            ))
            title_box.add_widget(MDLabel(
                text=time_str,
                font_size=DS.TYPOGRAPHY['caption'],
                theme_text_color='Custom',
                text_color=DS.COLORS['text_hint']
            ))
            header.add_widget(title_box)
            
            card.add_widget(header)
            
            # Message
            message = notif['message']
            max_msg_len = 80 if Window.width < 400 else 100
            if len(message) > max_msg_len:
                message = message[:max_msg_len] + "..."
            
            card.add_widget(MDLabel(
                text=message,
                font_size=DS.TYPOGRAPHY['body2'],
                theme_text_color='Custom',
                text_color=DS.COLORS['text_secondary'],
                size_hint_y=None,
                height=dp(44),
                padding=(DS.SPACING['sm'], 0)
            ))
            
            self.list_container.add_widget(card)
    
    def clear_notifications(self):
        main_screen = self.manager.get_screen('main')
        main_screen.notification_history = []
        main_screen.notification_count = 0
        main_screen.update_bell_icon()
        self.refresh_list()
        
        Snackbar(
            text="All notifications cleared",
            bg_color=DS.COLORS['success']
        ).open()
    
    def go_back(self):
        self.manager.transition.direction = 'right'
        self.manager.current = 'main'


# ============================================================================
# APP CLASS
# ============================================================================

class MontrealCompanionApp(MDApp):
    user_id = StringProperty(None)
    preferences = DictProperty({})
    latitude = NumericProperty(45.5017)
    longitude = NumericProperty(-73.5673)
    
    def build(self):
        # Apply custom theme (KivyMD 1.2.0 compatible)
        self.theme_cls.primary_palette = "Teal"  # Closest to jade green
        self.theme_cls.accent_palette = "Green"
        self.theme_cls.theme_style = "Light"
        self.theme_cls.material_style = "M3"
        
        # Note: In KivyMD 1.2.0, primary_color is read-only
        # We use our Design System colors directly in components
        
        sm = MDScreenManager()
        sm.add_widget(WelcomeScreen(name='welcome'))
        sm.add_widget(PreferencesScreen(name='preferences'))
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(NotificationHistoryScreen(name='notifications'))
        
        return sm
    
    def on_start(self):
        if GPS_AVAILABLE:
            try:
                if platform == 'android':
                    request_permissions([Permission.ACCESS_FINE_LOCATION])
                gps.configure(on_location=self.on_gps_location)
                gps.start(minTime=10000, minDistance=10)
            except Exception as e:
                logging.warning(f"GPS Error: {e}")
    
    def on_gps_location(self, **kwargs):
        self.latitude = kwargs.get('lat', self.latitude)
        self.longitude = kwargs.get('lon', self.longitude)
    
    def on_stop(self):
        try:
            main_screen = self.root.get_screen('main')
            if main_screen.notification_client:
                main_screen.notification_client.disconnect()
        except:
            pass


if __name__ == '__main__':
    MontrealCompanionApp().run()

