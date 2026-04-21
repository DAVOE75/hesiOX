/**
 * Theme Switcher for hesiOX
 * Handles light/dark theme toggle with localStorage persistence
 */

(function () {
    'use strict';

    const THEME_KEY = 'hesiox-theme';
    const THEME_DARK = 'dark';
    const THEME_LIGHT = 'light';

    /**
     * Get current theme from localStorage or default to dark
     */
    function getCurrentTheme() {
        return localStorage.getItem(THEME_KEY) || THEME_DARK;
    }

    /**
     * Apply theme to document
     */
    function applyTheme(theme) {
        if (theme === THEME_LIGHT) {
            document.documentElement.setAttribute('data-theme', 'light');
            document.body.setAttribute('data-theme', 'light');
        } else {
            document.documentElement.removeAttribute('data-theme');
            document.body.removeAttribute('data-theme');
        }

        // Update toggle button icon if it exists
        updateToggleIcon(theme);
    }

    /**
     * Update all toggle buttons' icons
     */
    function updateToggleIcon(theme) {
        const toggles = document.querySelectorAll('#theme-toggle, .theme-switcher-toggle');
        toggles.forEach(btn => {
            const icon = btn.querySelector('i');
            if (icon) {
                if (theme === THEME_LIGHT) {
                    icon.className = 'fa-solid fa-moon';
                    btn.title = 'Cambiar a modo oscuro';
                } else {
                    icon.className = 'fa-solid fa-sun';
                    btn.title = 'Cambiar a modo claro';
                }
            }
        });
    }

    /**
     * Toggle theme
     */
    function toggleTheme() {
        const currentTheme = getCurrentTheme();
        const newTheme = currentTheme === THEME_DARK ? THEME_LIGHT : THEME_DARK;

        localStorage.setItem(THEME_KEY, newTheme);
        applyTheme(newTheme);

        // Add smooth transition class
        document.body.classList.add('theme-transitioning');
        setTimeout(() => {
            document.body.classList.remove('theme-transitioning');
        }, 300);
    }

    /**
     * Initialize theme on page load
     */
    function initTheme() {
        const theme = getCurrentTheme();
        applyTheme(theme);

        // Add event listeners to all matching buttons
        const toggles = document.querySelectorAll('#theme-toggle, .theme-switcher-toggle');
        toggles.forEach(btn => {
            // Remove any existing listener to be safe (though this script usually runs once)
            btn.removeEventListener('click', toggleTheme);
            btn.addEventListener('click', toggleTheme);
        });
    }

    // Apply theme immediately to prevent flash
    applyTheme(getCurrentTheme());

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTheme);
    } else {
        initTheme();
    }

    // Expose toggle function globally for manual calls
    window.toggleTheme = toggleTheme;
})();
