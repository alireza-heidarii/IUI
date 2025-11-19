"""
Montreal Travel Companion - Android App
Beautiful, Production-Ready UI with Modern Design System
Built with Kivy following Nielsen's 10 Usability Heuristics
"""

import os
os.environ['KIVY_NO_CONSOLELOG'] = '0'

# Configure Kivy BEFORE importing anything
from kivy.config import Config
Config.set('kivy', 'log_level', 'warning')
Config.set('kivy', 'keyboard_mode', 'systemanddock')  # Use system keyboard
Config.set('kivy', 'keyboard_layout', 'qwerty')
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.checkbox import CheckBox
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.properties import StringProperty, BooleanProperty, ListProperty, NumericProperty, ObjectProperty
from kivy.metrics import dp, sp
from kivy.core.window import Window
from kivy.utils import get_color_from_hex, platform
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse, Line
from kivy.animation import Animation
from datetime import datetime
import requests
import json
import threading
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GPS support
try:
    from plyer import gps
    if platform == 'android':
        from android.permissions import request_permissions, Permission
    GPS_AVAILABLE = True
except ImportError:
    GPS_AVAILABLE = False
    logger.warning("GPS not available - plyer or android permissions not found")

# Set window size for testing (comment out for actual mobile)
Window.size = (400, 700)

# API Configuration
API_BASE_URL = "http://localhost:8000"  # Change to your API URL
# For Android emulator: "http://10.0.2.2:8000"
# For real device: "http://YOUR_COMPUTER_IP:8000"

# Modern Color Palette - Beautiful Gradient Design
COLORS = {
    'primary': get_color_from_hex('#6366F1'),        # Indigo
    'primary_dark': get_color_from_hex('#4F46E5'),   # Darker Indigo
    'secondary': get_color_from_hex('#EC4899'),      # Pink
    'accent': get_color_from_hex('#8B5CF6'),         # Purple
    'success': get_color_from_hex('#10B981'),        # Green
    'warning': get_color_from_hex('#F59E0B'),        # Amber
    'error': get_color_from_hex('#EF4444'),          # Red
    'info': get_color_from_hex('#3B82F6'),           # Blue
    
    # Backgrounds
    'bg_primary': get_color_from_hex('#FFFFFF'),     # White
    'bg_secondary': get_color_from_hex('#F9FAFB'),   # Gray 50
    'bg_card': get_color_from_hex('#FFFFFF'),        # White
    'bg_dark': get_color_from_hex('#1F2937'),        # Gray 800
    
    # Text
    'text_primary': get_color_from_hex('#111827'),   # Gray 900
    'text_secondary': get_color_from_hex('#6B7280'), # Gray 500
    'text_white': get_color_from_hex('#FFFFFF'),     # White
    'text_muted': get_color_from_hex('#9CA3AF'),     # Gray 400
    
    # Borders
    'border': get_color_from_hex('#E5E7EB'),         # Gray 200
    'border_dark': get_color_from_hex('#D1D5DB'),    # Gray 300
}


class ModernButton(Button):
    """Beautiful modern button with gradient and shadow"""
    button_type = StringProperty('primary')
    
    def __init__(self, **kwargs):
        self.button_type = kwargs.pop('button_type', 'primary')
        super().__init__(**kwargs)
        
        self.background_color = (0, 0, 0, 0)
        self.background_normal = ''
        self.color = COLORS['text_white']
        self.bold = True
        self.size_hint_y = None
        self.height = dp(52)
        self.font_size = sp(16)
        
        self.bind(pos=self.update_canvas, size=self.update_canvas)
        self.bind(on_press=self.on_button_press)
        self.bind(on_release=self.on_button_release)
    
    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            # Shadow
            Color(0, 0, 0, 0.1)
            RoundedRectangle(
                pos=(self.x, self.y - dp(2)),
                size=(self.width, self.height),
                radius=[dp(12)]
            )
            
            # Button background
            if self.button_type == 'primary':
                Color(*COLORS['primary'])
            elif self.button_type == 'secondary':
                Color(*COLORS['secondary'])
            elif self.button_type == 'success':
                Color(*COLORS['success'])
            elif self.button_type == 'danger':
                Color(*COLORS['error'])
            else:
                Color(*COLORS['primary'])
            
            RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(12)]
            )
    
    def on_button_press(self, instance):
        anim = Animation(height=dp(48), duration=0.1)
        anim.start(self)
    
    def on_button_release(self, instance):
        anim = Animation(height=dp(52), duration=0.1)
        anim.start(self)


class ModernCard(BoxLayout):
    """Beautiful card with shadow and rounded corners"""
    
    def __init__(self, elevation=2, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = dp(20)
        self.spacing = dp(12)
        self.size_hint_y = None
        self.elevation = elevation
        self.bind(minimum_height=self.setter('height'))
        self.bind(pos=self.update_canvas, size=self.update_canvas)
    
    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            # Shadow layers for elevation effect
            for i in range(self.elevation):
                alpha = 0.05 - (i * 0.01)
                Color(0, 0, 0, alpha)
                RoundedRectangle(
                    pos=(self.x - i, self.y - i),
                    size=(self.width + i*2, self.height + i*2),
                    radius=[dp(16)]
                )
            
            # Card background
            Color(*COLORS['bg_card'])
            RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(16)]
            )


class ModernInput(TextInput):
    """Beautiful modern text input with WORKING keyboard"""
    
    def __init__(self, **kwargs):
        # Extract multiline before calling super
        multiline = kwargs.pop('multiline', False)
        super().__init__(**kwargs)
        
        # Essential settings for keyboard input
        self.background_color = (0, 0, 0, 0)
        self.foreground_color = COLORS['text_primary']
        self.cursor_color = COLORS['primary']
        self.size_hint_y = None
        self.height = dp(56)  # Bigger for easier clicking
        self.padding = [dp(18), dp(18)]
        self.font_size = sp(17)  # Bigger font
        self.multiline = multiline
        self.write_tab = False
        
        # CRITICAL: Allow keyboard focus
        self.focus = False
        self.is_focusable = True
        
        self.bind(pos=self.update_canvas, size=self.update_canvas)
        self.bind(focus=self.on_focus_change)
    
    def on_touch_down(self, touch):
        """Handle touch to ensure focus"""
        if self.collide_point(*touch.pos):
            self.focus = True
            return super().on_touch_down(touch)
        return super().on_touch_down(touch)
    
    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            # Border
            if self.focus:
                Color(*COLORS['primary'])
            else:
                Color(*COLORS['border'])
            
            Line(
                rounded_rectangle=(
                    self.x, self.y, self.width, self.height,
                    dp(12), dp(12), dp(12), dp(12)
                ),
                width=dp(2)
            )
            
            # Background
            Color(*COLORS['bg_primary'])
            RoundedRectangle(
                pos=(self.x + dp(1), self.y + dp(1)),
                size=(self.width - dp(2), self.height - dp(2)),
                radius=[dp(11)]
            )
    
    def on_focus_change(self, instance, value):
        self.update_canvas()


class NotificationBadge(Label):
    """Red notification badge with count"""
    count = NumericProperty(0)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(20), dp(20))
        self.font_size = sp(11)
        self.bold = True
        self.color = COLORS['text_white']
        self.bind(count=self.update_text)
        self.bind(pos=self.update_canvas, size=self.update_canvas)
    
    def update_text(self, *args):
        if self.count > 0:
            self.text = str(min(self.count, 99))
            self.opacity = 1
        else:
            self.text = ''
            self.opacity = 0
    
    def update_canvas(self, *args):
        self.canvas.before.clear()
        if self.count > 0:
            with self.canvas.before:
                Color(*COLORS['error'])
                Ellipse(pos=self.pos, size=self.size)


class WelcomeScreen(Screen):
    """Beautiful welcome screen with gradient background"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        main_layout = BoxLayout(orientation='vertical')
        
        with main_layout.canvas.before:
            Color(*COLORS['primary'])
            self.bg_rect = Rectangle(pos=main_layout.pos, size=main_layout.size)
            Color(*COLORS['accent'], 0.3)
            self.gradient_rect = Rectangle(pos=main_layout.pos, size=main_layout.size)
        
        main_layout.bind(pos=self.update_bg, size=self.update_bg)
        
        content = BoxLayout(orientation='vertical', padding=dp(30), spacing=dp(30))
        content.add_widget(Widget(size_hint_y=0.2))
        
        icon_label = Label(
            text='🗺️',
            font_size=sp(80),
            size_hint_y=None,
            height=dp(120)
        )
        content.add_widget(icon_label)
        
        title = Label(
            text='Montreal\nTravel Companion',
            font_size=sp(36),
            bold=True,
            color=COLORS['text_white'],
            halign='center',
            size_hint_y=None,
            height=dp(100)
        )
        content.add_widget(title)
        
        subtitle = Label(
            text='Your AI-powered travel guide\nfor discovering Montreal',
            font_size=sp(16),
            color=COLORS['text_white'],
            halign='center',
            size_hint_y=None,
            height=dp(50),
            opacity=0.9
        )
        content.add_widget(subtitle)
        
        content.add_widget(Widget(size_hint_y=0.2))
        
        features_layout = BoxLayout(orientation='vertical', spacing=dp(12), size_hint_y=None, height=dp(180))
        
        features = [
            ('📍', 'Real-time GPS Location'),
            ('🌤️', 'Weather-Aware Suggestions'),
            ('🍽️', 'Personalized Dining'),
            ('🔔', 'Smart Notifications')
        ]
        
        for icon, text in features:
            feature_box = BoxLayout(size_hint_y=None, height=dp(40))
            feature_box.add_widget(Label(text=icon, font_size=sp(24), size_hint_x=0.2))
            feature_box.add_widget(Label(
                text=text,
                font_size=sp(14),
                color=COLORS['text_white'],
                halign='left',
                text_size=(dp(250), None),
                size_hint_x=0.8
            ))
            features_layout.add_widget(feature_box)
        
        content.add_widget(features_layout)
        content.add_widget(Widget(size_hint_y=0.2))
        
        btn = ModernButton(text='Get Started →', button_type='success')
        btn.bind(on_press=self.go_to_preferences)
        content.add_widget(btn)
        
        main_layout.add_widget(content)
        self.add_widget(main_layout)
    
    def update_bg(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size
        self.gradient_rect.pos = instance.pos
        self.gradient_rect.size = instance.size
    
    def go_to_preferences(self, instance):
        self.manager.transition = FadeTransition(duration=0.3)
        self.manager.current = 'preferences'


class PreferencesScreen(Screen):
    """Beautiful preferences screen with modern inputs"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        main_layout = BoxLayout(orientation='vertical')
        
        # Header
        header = BoxLayout(size_hint_y=None, height=dp(70), padding=[dp(20), dp(15)])
        with header.canvas.before:
            Color(*COLORS['bg_primary'])
            self.header_bg = Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=self.update_header_bg, size=self.update_header_bg)
        
        back_btn = Button(
            text='←',
            font_size=sp(28),
            size_hint_x=0.15,
            background_color=(0, 0, 0, 0),
            color=COLORS['primary']
        )
        back_btn.bind(on_press=self.go_back)
        
        header_title = Label(
            text='Your Preferences',
            font_size=sp(24),
            bold=True,
            color=COLORS['text_primary']
        )
        
        header.add_widget(back_btn)
        header.add_widget(header_title)
        header.add_widget(Widget(size_hint_x=0.15))
        
        # Scrollable content
        scroll = ScrollView()
        scroll.bar_width = dp(4)
        scroll.bar_color = COLORS['primary']
        
        content = BoxLayout(
            orientation='vertical',
            spacing=dp(20),
            size_hint_y=None,
            padding=[dp(20), dp(20)]
        )
        content.bind(minimum_height=content.setter('height'))
        
        # User ID Card
        user_card = ModernCard(elevation=2)
        user_card.add_widget(Label(
            text='👤 User ID',
            font_size=sp(18),
            bold=True,
            color=COLORS['text_primary'],
            size_hint_y=None,
            height=dp(30),
            halign='left',
            text_size=(Window.width - dp(80), None)
        ))
        self.user_id_input = ModernInput(hint_text='Enter your ID (e.g., user123)')
        user_card.add_widget(self.user_id_input)
        content.add_widget(user_card)
        
        # Activity Type Card
        activity_card = ModernCard(elevation=2)
        activity_card.add_widget(Label(
            text='🎯 Activity Preference',
            font_size=sp(18),
            bold=True,
            color=COLORS['text_primary'],
            size_hint_y=None,
            height=dp(30),
            halign='left',
            text_size=(Window.width - dp(80), None)
        ))
        
        activity_btns = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(12))
        self.indoor_btn = ModernButton(text='🏠 Indoor', button_type='secondary')
        self.outdoor_btn = ModernButton(text='🌳 Outdoor', button_type='primary')
        self.activity_type = "outdoor"
        
        self.indoor_btn.bind(on_press=self.select_indoor)
        self.outdoor_btn.bind(on_press=self.select_outdoor)
        
        activity_btns.add_widget(self.indoor_btn)
        activity_btns.add_widget(self.outdoor_btn)
        activity_card.add_widget(activity_btns)
        content.add_widget(activity_card)
        
        # Cuisine Card
        cuisine_card = ModernCard(elevation=2)
        cuisine_card.add_widget(Label(
            text='🍽️ Favorite Cuisines',
            font_size=sp(18),
            bold=True,
            color=COLORS['text_primary'],
            size_hint_y=None,
            height=dp(30),
            halign='left',
            text_size=(Window.width - dp(80), None)
        ))
        
        cuisines = [
            ('🍝', 'Italian'), ('🍱', 'Japanese'),
            ('🥐', 'French'), ('🌮', 'Mexican'),
            ('🥡', 'Chinese'), ('🍛', 'Indian'),
            ('🍔', 'Burgers'), ('☕', 'Cafe')
        ]
        
        self.cuisine_checkboxes = {}
        cuisine_grid = GridLayout(cols=2, spacing=dp(10), size_hint_y=None)
        cuisine_grid.bind(minimum_height=cuisine_grid.setter('height'))
        
        for icon, cuisine in cuisines:
            cb_layout = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(10))
            cb_layout.padding = [dp(10), dp(5)]
            
            with cb_layout.canvas.before:
                Color(*COLORS['bg_secondary'])
                cb_bg = RoundedRectangle(
                    pos=cb_layout.pos,
                    size=cb_layout.size,
                    radius=[dp(10)]
                )
                cb_layout.bind(pos=lambda i, v, bg=cb_bg: setattr(bg, 'pos', v),
                             size=lambda i, v, bg=cb_bg: setattr(bg, 'size', v))
            
            cb = CheckBox(size_hint_x=0.2, color=COLORS['primary'])
            lbl = Label(
                text=f'{icon} {cuisine}',
                color=COLORS['text_primary'],
                size_hint_x=0.8,
                halign='left',
                text_size=(dp(100), None),
                font_size=sp(14)
            )
            cb_layout.add_widget(cb)
            cb_layout.add_widget(lbl)
            cuisine_grid.add_widget(cb_layout)
            self.cuisine_checkboxes[cuisine] = cb
        
        self.cuisine_checkboxes["Italian"].active = True
        cuisine_card.add_widget(cuisine_grid)
        content.add_widget(cuisine_card)
        
        # Meal Times Card
        meal_card = ModernCard(elevation=2)
        meal_card.add_widget(Label(
            text='⏰ Meal Times',
            font_size=sp(18),
            bold=True,
            color=COLORS['text_primary'],
            size_hint_y=None,
            height=dp(30),
            halign='left',
            text_size=(Window.width - dp(80), None)
        ))
        
        meal_grid = GridLayout(cols=2, spacing=dp(12), size_hint_y=None, height=dp(170))
        
        meals = [('🌅', 'Breakfast', '08:00'),
                ('☀️', 'Lunch', '12:30'),
                ('🌙', 'Dinner', '19:00')]
        
        self.meal_inputs = {}
        for icon, meal, default_time in meals:
            meal_grid.add_widget(Label(
                text=f'{icon} {meal}:',
                color=COLORS['text_primary'],
                font_size=sp(14),
                halign='right',
                text_size=(dp(100), None)
            ))
            time_input = ModernInput(text=default_time)
            self.meal_inputs[meal.lower()] = time_input
            meal_grid.add_widget(time_input)
        
        meal_card.add_widget(meal_grid)
        content.add_widget(meal_card)
        
        # Location Card
        location_card = ModernCard(elevation=2)
        location_card.add_widget(Label(
            text='📍 Location',
            font_size=sp(18),
            bold=True,
            color=COLORS['text_primary'],
            size_hint_y=None,
            height=dp(30),
            halign='left',
            text_size=(Window.width - dp(80), None)
        ))
        
        app = App.get_running_app()
        if GPS_AVAILABLE and hasattr(app, 'gps_location') and app.gps_location:
            gps_status = Label(
                text=f'✅ GPS Active',
                font_size=sp(13),
                color=COLORS['success'],
                size_hint_y=None,
                height=dp(25),
                halign='left',
                text_size=(Window.width - dp(80), None)
            )
            location_card.add_widget(gps_status)
        
        self.latitude_input = ModernInput(
            text=f"{app.latitude if hasattr(app, 'latitude') else 45.5017}",
            hint_text="Latitude"
        )
        self.longitude_input = ModernInput(
            text=f"{app.longitude if hasattr(app, 'longitude') else -73.5673}",
            hint_text="Longitude"
        )
        location_card.add_widget(self.latitude_input)
        location_card.add_widget(self.longitude_input)
        content.add_widget(location_card)
        
        # Save Button
        save_btn = ModernButton(text='💾 Save Preferences', button_type='success')
        save_btn.bind(on_press=self.save_preferences)
        content.add_widget(save_btn)
        
        scroll.add_widget(content)
        main_layout.add_widget(header)
        main_layout.add_widget(scroll)
        
        self.add_widget(main_layout)
    
    def update_header_bg(self, instance, value):
        self.header_bg.pos = instance.pos
        self.header_bg.size = instance.size
    
    def select_indoor(self, instance):
        self.activity_type = "indoor"
        self.indoor_btn.button_type = 'primary'
        self.outdoor_btn.button_type = 'secondary'
        self.indoor_btn.update_canvas()
        self.outdoor_btn.update_canvas()
    
    def select_outdoor(self, instance):
        self.activity_type = "outdoor"
        self.outdoor_btn.button_type = 'primary'
        self.indoor_btn.button_type = 'secondary'
        self.indoor_btn.update_canvas()
        self.outdoor_btn.update_canvas()
    
    def go_back(self, instance):
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'welcome'
    
    def save_preferences(self, instance):
        user_id = self.user_id_input.text.strip()
        if not user_id:
            self.show_error("Please enter a User ID")
            return
        
        selected_cuisines = [
            cuisine for cuisine, cb in self.cuisine_checkboxes.items()
            if cb.active
        ]
        
        if not selected_cuisines:
            self.show_error("Please select at least one cuisine")
            return
        
        try:
            meal_times = {}
            for meal, input_widget in self.meal_inputs.items():
                time = input_widget.text.strip()
                hour, minute = time.split(':')
                if not (0 <= int(hour) <= 23 and 0 <= int(minute) <= 59):
                    raise ValueError
                meal_times[meal] = time
        except:
            self.show_error("Invalid time format. Use HH:MM (e.g., 08:00)")
            return
        
        self.show_loading("Saving preferences...")
        
        preferences_data = {
            "user_id": user_id,
            "activity_type": self.activity_type,
            "meal_times": meal_times,
            "preferred_cuisines": selected_cuisines
        }
        
        app = App.get_running_app()
        app.user_id = user_id
        app.preferences = preferences_data
        app.latitude = float(self.latitude_input.text)
        app.longitude = float(self.longitude_input.text)
        
        def send_to_api():
            try:
                response = requests.post(
                    f"{API_BASE_URL}/api/preferences",
                    json=preferences_data,
                    timeout=10
                )
                Clock.schedule_once(lambda dt: self.on_save_success(response), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self.on_save_error(str(e)), 0)
        
        threading.Thread(target=send_to_api, daemon=True).start()
    
    def on_save_success(self, response):
        self.dismiss_loading()
        if response.status_code == 200:
            self.show_success("Preferences saved successfully!")
            Clock.schedule_once(lambda dt: self.go_to_main(), 1.5)
        else:
            self.show_error(f"Error: {response.text}")
    
    def on_save_error(self, error_msg):
        self.dismiss_loading()
        self.show_error(f"Connection error\n\nMake sure API server is running")
    
    def go_to_main(self):
        self.manager.transition = FadeTransition(duration=0.3)
        self.manager.current = 'main'
    
    def show_loading(self, message):
        content = BoxLayout(orientation='vertical', spacing=dp(20), padding=dp(30))
        content.add_widget(Label(
            text=message,
            color=COLORS['text_primary'],
            font_size=sp(16)
        ))
        pb = ProgressBar(max=100)
        pb.value = 100
        content.add_widget(pb)
        
        self.loading_popup = Popup(
            title='Please Wait',
            content=content,
            size_hint=(0.8, 0.25),
            auto_dismiss=False
        )
        self.loading_popup.open()
    
    def dismiss_loading(self):
        if hasattr(self, 'loading_popup'):
            self.loading_popup.dismiss()
    
    def show_error(self, message):
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(25))
        error_label = Label(
            text=f"❌ {message}",
            color=COLORS['error'],
            halign='center',
            font_size=sp(15)
        )
        content.add_widget(error_label)
        
        ok_btn = ModernButton(text="OK", button_type='danger')
        content.add_widget(ok_btn)
        
        popup = Popup(
            title='Error',
            content=content,
            size_hint=(0.85, 0.35)
        )
        ok_btn.bind(on_press=popup.dismiss)
        popup.open()
    
    def show_success(self, message):
        content = Label(
            text=f"✅ {message}",
            color=COLORS['success'],
            halign='center',
            font_size=sp(16)
        )
        
        popup = Popup(
            title='Success',
            content=content,
            size_hint=(0.7, 0.25),
            auto_dismiss=True
        )
        popup.open()


class MainScreen(Screen):
    """Beautiful main screen with modern cards and WORKING notifications"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.notifications = []
        self.last_context = {}
        
        self.layout = BoxLayout(orientation='vertical')
        
        # Modern Header with Gradient
        header = BoxLayout(size_hint_y=None, height=dp(70), padding=[dp(15), dp(10)], spacing=dp(10))
        with header.canvas.before:
            Color(*COLORS['primary'])
            self.header_bg = Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=self.update_header_bg, size=self.update_header_bg)
        
        # Menu button
        menu_btn = Button(
            text='☰',
            font_size=sp(28),
            size_hint_x=0.12,
            background_color=(0, 0, 0, 0),
            color=COLORS['text_white']
        )
        menu_btn.bind(on_press=self.show_menu)
        
        # Title
        title_layout = BoxLayout(orientation='vertical', spacing=0)
        header_title = Label(
            text='Montreal Travel',
            font_size=sp(18),
            bold=True,
            color=COLORS['text_white'],
            halign='left',
            text_size=(dp(200), None)
        )
        header_subtitle = Label(
            text='Your AI Guide',
            font_size=sp(11),
            color=COLORS['text_white'],
            opacity=0.8,
            halign='left',
            text_size=(dp(200), None)
        )
        title_layout.add_widget(header_title)
        title_layout.add_widget(header_subtitle)
        
        # Notification button WITH badge
        notif_container = BoxLayout(size_hint_x=0.12, orientation='vertical')
        notif_btn_layout = BoxLayout(size_hint=(1, 0.8))
        
        self.notification_btn = Button(
            text='🔔',
            font_size=sp(24),
            background_color=(0, 0, 0, 0),
            color=COLORS['text_white']
        )
        self.notification_btn.bind(on_press=self.show_notifications)
        notif_btn_layout.add_widget(self.notification_btn)
        
        # Badge positioned in top-right
        badge_container = BoxLayout(size_hint=(1, 0.2))
        badge_container.add_widget(Widget(size_hint_x=0.5))
        self.notif_badge = NotificationBadge()
        badge_container.add_widget(self.notif_badge)
        
        notif_container.add_widget(badge_container)
        notif_container.add_widget(notif_btn_layout)
        
        # Refresh button
        refresh_btn = Button(
            text='🔄',
            font_size=sp(24),
            size_hint_x=0.12,
            background_color=(0, 0, 0, 0),
            color=COLORS['text_white']
        )
        refresh_btn.bind(on_press=self.refresh_recommendations)
        
        header.add_widget(menu_btn)
        header.add_widget(title_layout)
        header.add_widget(notif_container)
        header.add_widget(refresh_btn)
        
        # Context Card
        self.context_card = ModernCard(elevation=3)
        self.context_card.size_hint_y = None
        self.context_card.height = dp(140)
        
        context_title = Label(
            text='📊 Current Context',
            font_size=sp(17),
            bold=True,
            color=COLORS['text_primary'],
            size_hint_y=None,
            height=dp(30),
            halign='left',
            text_size=(Window.width - dp(80), None)
        )
        self.context_card.add_widget(context_title)
        
        self.context_grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None, height=dp(90))
        self.context_card.add_widget(self.context_grid)
        
        # Stats Cards
        self.stats_layout = BoxLayout(
            orientation='horizontal',
            spacing=dp(12),
            size_hint_y=None,
            height=dp(90),
            padding=[dp(15), 0]
        )
        
        # Scrollable Recommendations
        self.scroll = ScrollView()
        self.scroll.bar_width = dp(4)
        self.scroll.bar_color = COLORS['primary']
        
        self.recommendations_layout = BoxLayout(
            orientation='vertical',
            spacing=dp(15),
            size_hint_y=None,
            padding=[dp(15), dp(15)]
        )
        self.recommendations_layout.bind(minimum_height=self.recommendations_layout.setter('height'))
        self.scroll.add_widget(self.recommendations_layout)
        
        # Assemble Layout
        self.layout.add_widget(header)
        self.layout.add_widget(Widget(size_hint_y=None, height=dp(5)))
        
        content_scroll = ScrollView()
        content_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(15), padding=[dp(15), 0])
        content_layout.bind(minimum_height=content_layout.setter('height'))
        content_layout.add_widget(self.context_card)
        content_layout.add_widget(self.stats_layout)
        content_layout.add_widget(Label(
            text='✨ Recommendations for You',
            font_size=sp(20),
            bold=True,
            color=COLORS['text_primary'],
            size_hint_y=None,
            height=dp(40),
            halign='left',
            text_size=(Window.width - dp(40), None)
        ))
        
        self.layout.add_widget(content_scroll)
        content_scroll.add_widget(content_layout)
        self.layout.add_widget(self.scroll)
        
        self.add_widget(self.layout)
    
    def update_header_bg(self, instance, value):
        self.header_bg.pos = instance.pos
        self.header_bg.size = instance.size
    
    def on_enter(self):
        self.load_recommendations()
        # Check for context changes every 60 seconds
        Clock.schedule_interval(self.check_context_changes, 60)
    
    def show_menu(self, instance):
        content = BoxLayout(orientation='vertical', spacing=dp(12), padding=dp(20))
        
        edit_btn = ModernButton(text='✏️ Edit Preferences', button_type='primary')
        about_btn = ModernButton(text='ℹ️ About', button_type='secondary')
        close_btn = ModernButton(text='Close', button_type='danger')
        
        edit_btn.bind(on_press=lambda x: self.go_to_preferences(popup))
        about_btn.bind(on_press=lambda x: self.show_about(popup))
        
        content.add_widget(edit_btn)
        content.add_widget(about_btn)
        content.add_widget(close_btn)
        
        popup = Popup(title='Menu', content=content, size_hint=(0.8, 0.4))
        close_btn.bind(on_press=popup.dismiss)
        popup.open()
    
    def go_to_preferences(self, popup):
        popup.dismiss()
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'preferences'
    
    def show_about(self, popup):
        popup.dismiss()
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(25))
        
        about_text = Label(
            text=(
                'Montreal Travel Companion\n'
                'Version 2.0\n\n'
                'AI-powered travel recommendations\n'
                'with real-time context awareness.\n\n'
                'Features:\n'
                '• GPS location tracking\n'
                '• Live weather integration\n'
                '• Smart notifications\n'
                '• Personalized suggestions'
            ),
            color=COLORS['text_primary'],
            halign='center',
            font_size=sp(14)
        )
        content.add_widget(about_text)
        
        ok_btn = ModernButton(text='OK', button_type='primary')
        content.add_widget(ok_btn)
        
        popup2 = Popup(title='About', content=content, size_hint=(0.85, 0.6))
        ok_btn.bind(on_press=popup2.dismiss)
        popup2.open()
    
    def show_notifications(self, instance):
        """Display notification history"""
        content = BoxLayout(orientation='vertical', spacing=dp(12), padding=dp(15))
        
        scroll = ScrollView()
        notif_layout = BoxLayout(orientation='vertical', spacing=dp(12), size_hint_y=None)
        notif_layout.bind(minimum_height=notif_layout.setter('height'))
        
        if not self.notifications:
            empty_label = Label(
                text='No notifications yet\n\n🔔',
                color=COLORS['text_secondary'],
                font_size=sp(16),
                size_hint_y=None,
                height=dp(100),
                halign='center'
            )
            notif_layout.add_widget(empty_label)
        else:
            for notif in reversed(self.notifications[-10:]):
                notif_card = BoxLayout(
                    orientation='vertical',
                    size_hint_y=None,
                    height=dp(90),
                    padding=dp(15),
                    spacing=dp(8)
                )
                
                with notif_card.canvas.before:
                    Color(*COLORS['bg_secondary'])
                    notif_bg = RoundedRectangle(
                        pos=notif_card.pos,
                        size=notif_card.size,
                        radius=[dp(12)]
                    )
                    notif_card.bind(
                        pos=lambda i, v, bg=notif_bg: setattr(bg, 'pos', v),
                        size=lambda i, v, bg=notif_bg: setattr(bg, 'size', v)
                    )
                
                title_label = Label(
                    text=notif.get('title', 'Notification'),
                    color=COLORS['primary'],
                    bold=True,
                    font_size=sp(15),
                    size_hint_y=0.4,
                    halign='left',
                    text_size=(Window.width - dp(90), None)
                )
                message_label = Label(
                    text=notif.get('message', ''),
                    color=COLORS['text_primary'],
                    font_size=sp(13),
                    size_hint_y=0.6,
                    halign='left',
                    text_size=(Window.width - dp(90), None)
                )
                
                notif_card.add_widget(title_label)
                notif_card.add_widget(message_label)
                notif_layout.add_widget(notif_card)
        
        scroll.add_widget(notif_layout)
        content.add_widget(scroll)
        
        close_btn = ModernButton(text='Close', button_type='primary')
        content.add_widget(close_btn)
        
        popup = Popup(
            title=f'🔔 Notifications ({len(self.notifications)})',
            content=content,
            size_hint=(0.92, 0.75)
        )
        close_btn.bind(on_press=popup.dismiss)
        popup.open()
        
        # Reset badge
        self.notif_badge.count = 0
    
    def add_notification(self, title, message):
        """Add notification - FIXED VERSION"""
        notification = {
            'title': title,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        self.notifications.append(notification)
        
        # Update badge - THIS IS THE KEY FIX
        self.notif_badge.count = len(self.notifications)
        
        # Show popup
        self.show_notification_popup(title, message)
        
        logger.info(f"✅ Notification added: {title} - Badge count: {self.notif_badge.count}")
    
    def show_notification_popup(self, title, message):
        """Show popup notification"""
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(25))
        
        title_label = Label(
            text=f'🔔 {title}',
            font_size=sp(18),
            bold=True,
            color=COLORS['primary'],
            size_hint_y=0.3
        )
        message_label = Label(
            text=message,
            color=COLORS['text_primary'],
            font_size=sp(14),
            size_hint_y=0.5,
            halign='center',
            text_size=(Window.width - dp(100), None)
        )
        ok_btn = ModernButton(text='OK', button_type='success')
        
        content.add_widget(title_label)
        content.add_widget(message_label)
        content.add_widget(ok_btn)
        
        popup = Popup(
            title='🔔 New Update',
            content=content,
            size_hint=(0.85, 0.4),
            auto_dismiss=False
        )
        ok_btn.bind(on_press=popup.dismiss)
        popup.open()
        
        # Auto dismiss after 3 seconds
        Clock.schedule_once(lambda dt: popup.dismiss(), 3)
    
    def check_context_changes(self, dt):
        """Check for context changes"""
        app = App.get_running_app()
        
        if not hasattr(app, 'preferences'):
            return
        
        def fetch_context():
            try:
                response = requests.post(
                    f"{API_BASE_URL}/api/weather",
                    json={
                        "latitude": app.latitude,
                        "longitude": app.longitude
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    weather_data = response.json()
                    current_context = {
                        'weather': weather_data.get('weather'),
                        'temperature': weather_data.get('temperature'),
                        'time_hour': datetime.now().hour
                    }
                    
                    Clock.schedule_once(lambda dt: self.compare_context(current_context), 0)
            except Exception as e:
                logger.error(f"Error checking context: {e}")
        
        threading.Thread(target=fetch_context, daemon=True).start()
    
    def compare_context(self, new_context):
        """Compare contexts and send notifications"""
        if not self.last_context:
            self.last_context = new_context
            return
        
        # Weather change
        if self.last_context.get('weather') != new_context.get('weather'):
            old_w = self.last_context.get('weather', 'unknown')
            new_w = new_context.get('weather', 'unknown')
            
            messages = {
                ('sunny', 'rainy'): ("Weather Alert", "It's raining! Consider indoor activities."),
                ('rainy', 'sunny'): ("Weather Alert", "Rain stopped! Great for outdoor activities."),
                ('sunny', 'snowy'): ("Weather Alert", "Snow! Winter activities available."),
                ('snowy', 'sunny'): ("Weather Alert", "Snow cleared! Outdoor activities recommended."),
            }
            
            key = (old_w, new_w)
            if key in messages:
                title, message = messages[key]
                self.add_notification(title, message)
                self.refresh_recommendations(None)
        
        # Temperature change
        old_temp = self.last_context.get('temperature', 0)
        new_temp = new_context.get('temperature', 0)
        if abs(old_temp - new_temp) >= 5:
            self.add_notification(
                "Temperature Change",
                f"Temperature: {old_temp}°C → {new_temp}°C"
            )
            self.refresh_recommendations(None)
        
        # Time period change
        def get_period(hour):
            if 5 <= hour < 8: return "Early Morning"
            elif 8 <= hour < 12: return "Morning"
            elif 12 <= hour < 17: return "Afternoon"
            elif 17 <= hour < 21: return "Evening"
            else: return "Night"
        
        old_hour = self.last_context.get('time_hour', 0)
        new_hour = new_context.get('time_hour', 0)
        
        if get_period(old_hour) != get_period(new_hour):
            period = get_period(new_hour)
            self.add_notification(
                f"{period} Activities",
                f"Discover activities for {period.lower()}!"
            )
            self.refresh_recommendations(None)
        
        self.last_context = new_context
    
    def refresh_recommendations(self, instance):
        self.load_recommendations()
    
    def load_recommendations(self):
        app = App.get_running_app()
        
        if not hasattr(app, 'preferences'):
            self.show_error("Please set your preferences first")
            return
        
        self.show_loading_indicator()
        
        request_data = {
            "preferences": app.preferences,
            "location": {
                "latitude": app.latitude,
                "longitude": app.longitude
            }
        }
        
        def fetch_data():
            try:
                response = requests.post(
                    f"{API_BASE_URL}/api/recommendations",
                    json=request_data,
                    timeout=10
                )
                Clock.schedule_once(lambda dt: self.on_load_success(response), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self.on_load_error(str(e)), 0)
        
        threading.Thread(target=fetch_data, daemon=True).start()
    
    def show_loading_indicator(self):
        self.recommendations_layout.clear_widgets()
        loading_label = Label(
            text='Loading recommendations...\n🔄',
            font_size=sp(18),
            color=COLORS['text_secondary'],
            size_hint_y=None,
            height=dp(120)
        )
        self.recommendations_layout.add_widget(loading_label)
    
    def on_load_success(self, response):
        if response.status_code == 200:
            data = response.json()
            self.display_recommendations(data)
        else:
            self.on_load_error(f"Server error: {response.status_code}")
    
    def on_load_error(self, error_msg):
        self.recommendations_layout.clear_widgets()
        error_label = Label(
            text=f'❌ Error loading\n\n{error_msg}',
            font_size=sp(14),
            color=COLORS['error'],
            size_hint_y=None,
            height=dp(150),
            halign='center'
        )
        self.recommendations_layout.add_widget(error_label)
    
    def display_recommendations(self, data):
        self.recommendations_layout.clear_widgets()
        
        context = data.get('context', {})
        self.update_context_display(context)
        
        self.last_context = {
            'weather': context.get('weather'),
            'temperature': context.get('temperature'),
            'time_hour': context.get('time_hour')
        }
        
        recommendations = data.get('recommendations', [])
        self.update_stats(recommendations)
        
        if not recommendations:
            empty_label = Label(
                text='No recommendations found\n\n😕\n\nTry adjusting your preferences',
                font_size=sp(15),
                color=COLORS['text_secondary'],
                size_hint_y=None,
                height=dp(180),
                halign='center'
            )
            self.recommendations_layout.add_widget(empty_label)
            return
        
        for i, rec in enumerate(recommendations, 1):
            rec_card = self.create_recommendation_card(i, rec)
            self.recommendations_layout.add_widget(rec_card)
    
    def update_context_display(self, context):
        self.context_grid.clear_widgets()
        
        time_str = f"{context.get('time_hour', 0)}:00"
        period = context.get('time_period', 'Unknown')
        weather = context.get('weather', 'Unknown')
        temp = context.get('temperature', '?')
        
        app = App.get_running_app()
        location_str = "GPS ✅" if (GPS_AVAILABLE and hasattr(app, 'gps_location') and app.gps_location) else "Default"
        
        items = [
            ('🕐', 'Time', f'{time_str} ({period})'),
            ('🌤️', 'Weather', weather.capitalize()),
            ('🌡️', 'Temp', f'{temp}°C'),
            ('📍', 'Location', location_str)
        ]
        
        for icon, label, value in items:
            icon_label = Label(
                text=icon,
                font_size=sp(20),
                size_hint_x=0.15
            )
            text_layout = BoxLayout(orientation='vertical', size_hint_x=0.85, spacing=0)
            label_widget = Label(
                text=label,
                color=COLORS['text_muted'],
                font_size=sp(11),
                halign='left',
                size_hint_y=0.4,
                text_size=(dp(150), None)
            )
            value_widget = Label(
                text=value,
                color=COLORS['primary'],
                font_size=sp(13),
                bold=True,
                halign='left',
                size_hint_y=0.6,
                text_size=(dp(150), None)
            )
            text_layout.add_widget(label_widget)
            text_layout.add_widget(value_widget)
            
            item_box = BoxLayout(spacing=dp(5))
            item_box.add_widget(icon_label)
            item_box.add_widget(text_layout)
            self.context_grid.add_widget(item_box)
    
    def update_stats(self, recommendations):
        self.stats_layout.clear_widgets()
        
        total = len(recommendations)
        restaurants = len([r for r in recommendations if r.get('type') == 'restaurant'])
        activities = total - restaurants
        
        stats = [
            (str(total), 'Total', COLORS['info']),
            (str(restaurants), 'Restaurants', COLORS['secondary']),
            (str(activities), 'Activities', COLORS['accent'])
        ]
        
        for value, label, color in stats:
            stat_card = BoxLayout(orientation='vertical', padding=dp(15))
            
            with stat_card.canvas.before:
                Color(*color, 0.1)
                stat_bg = RoundedRectangle(
                    pos=stat_card.pos,
                    size=stat_card.size,
                    radius=[dp(14)]
                )
                stat_card.bind(
                    pos=lambda i, v, bg=stat_bg: setattr(bg, 'pos', v),
                    size=lambda i, v, bg=stat_bg: setattr(bg, 'size', v)
                )
            
            stat_value = Label(
                text=value,
                font_size=sp(28),
                bold=True,
                color=color,
                size_hint_y=0.6
            )
            stat_label = Label(
                text=label,
                font_size=sp(12),
                color=COLORS['text_secondary'],
                size_hint_y=0.4
            )
            
            stat_card.add_widget(stat_value)
            stat_card.add_widget(stat_label)
            self.stats_layout.add_widget(stat_card)
    
    def create_recommendation_card(self, index, rec):
        """Create beautiful recommendation card with BIG readable fonts"""
        card = ModernCard(elevation=3)
        card.spacing = dp(15)  # More spacing
        card.padding = dp(25)  # More padding
        
        # NUMBER badge in top-left corner
        number_box = BoxLayout(size_hint_y=None, height=dp(40))
        number_label = Label(
            text=str(index),
            font_size=sp(24),
            bold=True,
            color=COLORS['text_white'],
            size_hint=(None, None),
            size=(dp(40), dp(40))
        )
        with number_label.canvas.before:
            Color(*COLORS['primary'])
            number_bg = Ellipse(pos=number_label.pos, size=number_label.size)
            number_label.bind(
                pos=lambda i, v, bg=number_bg: setattr(bg, 'pos', v),
                size=lambda i, v, bg=number_bg: setattr(bg, 'size', v)
            )
        number_box.add_widget(number_label)
        number_box.add_widget(Widget())
        card.add_widget(number_box)
        
        # NAME - BIG and bold
        name_label = Label(
            text=rec.get("name", "Unknown"),
            font_size=sp(22),
            bold=True,
            color=COLORS['text_primary'],
            size_hint_y=None,
            height=dp(60),
            halign='left',
            valign='top',
            text_size=(Window.width - dp(90), None)
        )
        card.add_widget(name_label)
        
        # TYPE and RATING row
        info_row = BoxLayout(size_hint_y=None, height=dp(35), spacing=dp(10))
        
        # Type badge
        type_label = Label(
            text=f'📍 {rec.get("type", "Unknown").title()}',
            font_size=sp(15),
            bold=True,
            color=COLORS['text_white'],
            size_hint=(None, None),
            size=(dp(160), dp(32))
        )
        with type_label.canvas.before:
            Color(*COLORS['secondary'])
            type_bg = RoundedRectangle(
                pos=type_label.pos,
                size=type_label.size,
                radius=[dp(16)]
            )
            type_label.bind(
                pos=lambda i, v, bg=type_bg: setattr(bg, 'pos', v),
                size=lambda i, v, bg=type_bg: setattr(bg, 'size', v)
            )
        info_row.add_widget(type_label)
        
        # Rating
        rating = rec.get('rating')
        if rating:
            rating_label = Label(
                text=f'⭐ {rating}',
                font_size=sp(18),
                bold=True,
                color=COLORS['warning'],
                size_hint_x=0.5
            )
            info_row.add_widget(rating_label)
        else:
            info_row.add_widget(Widget())
        
        card.add_widget(info_row)
        
        # DESCRIPTION - Bigger font
        description = rec.get('description', 'No description available')
        desc_label = Label(
            text=description,
            font_size=sp(16),
            color=COLORS['text_secondary'],
            size_hint_y=None,
            height=dp(50),
            halign='left',
            valign='top',
            text_size=(Window.width - dp(90), None)
        )
        card.add_widget(desc_label)
        
        # CUISINE (for restaurants)
        cuisines = rec.get('cuisines', [])
        if cuisines and len(cuisines) > 0:
            cuisine_box = BoxLayout(size_hint_y=None, height=dp(35), spacing=dp(8))
            cuisine_label = Label(
                text=f'🍽️ {", ".join(cuisines[:3])}',
                font_size=sp(15),
                color=COLORS['accent'],
                bold=True,
                halign='left',
                text_size=(Window.width - dp(90), None)
            )
            cuisine_box.add_widget(cuisine_label)
            card.add_widget(cuisine_box)
        
        # ADDRESS - Bigger and clearer
        address_box = BoxLayout(size_hint_y=None, height=dp(55), padding=[dp(12), dp(10)])
        with address_box.canvas.before:
            Color(*COLORS['info'], 0.1)
            addr_bg = RoundedRectangle(
                pos=address_box.pos,
                size=address_box.size,
                radius=[dp(12)]
            )
            address_box.bind(
                pos=lambda i, v, bg=addr_bg: setattr(bg, 'pos', v),
                size=lambda i, v, bg=addr_bg: setattr(bg, 'size', v)
            )
        
        address_label = Label(
            text=f'📍 {rec.get("address", "Address not available")}',
            font_size=sp(15),
            color=COLORS['info'],
            bold=True,
            halign='left',
            valign='middle',
            text_size=(Window.width - dp(110), None)
        )
        address_box.add_widget(address_label)
        card.add_widget(address_box)
        
        # DISTANCE - Big and prominent
        distance = rec.get('distance')
        if distance:
            dist_km = distance / 1000
            distance_box = BoxLayout(size_hint_y=None, height=dp(35))
            distance_label = Label(
                text=f'📏 {dist_km:.2f} km away',
                font_size=sp(17),
                bold=True,
                color=COLORS['success'] if dist_km < 1 else COLORS['info'],
                halign='left',
                text_size=(Window.width - dp(90), None)
            )
            distance_box.add_widget(distance_label)
            card.add_widget(distance_box)
        
        # REASON - Highlighted and bigger
        reason = rec.get('reason', '')
        if reason:
            reason_box = BoxLayout(size_hint_y=None, padding=[dp(15), dp(12)])
            reason_box.bind(minimum_height=reason_box.setter('height'))
            
            with reason_box.canvas.before:
                Color(*COLORS['accent'], 0.15)
                reason_bg = RoundedRectangle(
                    pos=reason_box.pos,
                    size=reason_box.size,
                    radius=[dp(12)]
                )
                reason_box.bind(
                    pos=lambda i, v, bg=reason_bg: setattr(bg, 'pos', v),
                    size=lambda i, v, bg=reason_bg: setattr(bg, 'size', v)
                )
            
            reason_label = Label(
                text=f'💡 Why we recommend:\n{reason}',
                font_size=sp(15),
                color=COLORS['accent'],
                bold=True,
                halign='left',
                valign='middle',
                text_size=(Window.width - dp(110), None),
                size_hint_y=None
            )
            reason_label.bind(texture_size=reason_label.setter('size'))
            reason_box.add_widget(reason_label)
            card.add_widget(reason_box)
        
        return card
    
    def show_error(self, message):
        content = Label(text=message, color=COLORS['error'])
        popup = Popup(title='Error', content=content, size_hint=(0.8, 0.3))
        popup.open()


class MontrealTravelApp(App):
    """Main Application"""
    
    def build(self):
        self.user_id = None
        self.preferences = None
        self.latitude = 45.5017
        self.longitude = -73.5673
        self.gps_location = None
        
        if platform == 'android':
            self.request_android_permissions()
        
        sm = ScreenManager()
        sm.add_widget(WelcomeScreen(name='welcome'))
        sm.add_widget(PreferencesScreen(name='preferences'))
        sm.add_widget(MainScreen(name='main'))
        
        return sm
    
    def request_android_permissions(self):
        try:
            request_permissions([
                Permission.ACCESS_FINE_LOCATION,
                Permission.ACCESS_COARSE_LOCATION,
                Permission.INTERNET
            ])
            logger.info("Permissions requested")
        except Exception as e:
            logger.error(f"Error requesting permissions: {e}")
    
    def start_gps(self):
        if not GPS_AVAILABLE:
            return False
        
        try:
            gps.configure(on_location=self.on_gps_location, on_status=self.on_gps_status)
            gps.start(minTime=1000, minDistance=10)
            logger.info("GPS started")
            return True
        except Exception as e:
            logger.error(f"Error starting GPS: {e}")
            return False
    
    def stop_gps(self):
        if GPS_AVAILABLE:
            try:
                gps.stop()
            except:
                pass
    
    def on_gps_location(self, **kwargs):
        self.gps_location = kwargs
        lat = kwargs.get('lat')
        lon = kwargs.get('lon')
        
        if lat and lon:
            from math import radians, sin, cos, sqrt, atan2
            
            old_lat, old_lon = self.latitude, self.longitude
            self.latitude = lat
            self.longitude = lon
            
            R = 6371
            lat1, lon1, lat2, lon2 = map(radians, [old_lat, old_lon, lat, lon])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            distance = R * c
            
            logger.info(f"GPS: {lat}, {lon} (moved {distance:.2f} km)")
            
            if distance > 0.25:
                try:
                    main_screen = self.root.get_screen('main')
                    main_screen.add_notification(
                        "Location Changed",
                        f"Moved {distance:.2f} km. Updating..."
                    )
                    main_screen.refresh_recommendations(None)
                except:
                    pass
    
    def on_gps_status(self, stype, status):
        logger.info(f"GPS status: {stype} = {status}")
    
    def on_start(self):
        if self.start_gps():
            logger.info("GPS enabled")
        else:
            logger.warning("Using default location")
    
    def on_stop(self):
        self.stop_gps()


if __name__ == '__main__':
    MontrealTravelApp().run()