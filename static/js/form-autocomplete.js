// =========================================================
// 🎯 AUTOCOMPLETAR INTELIGENTE MEJORADO
// =========================================================

class SmartAutocomplete {
    constructor() {
        this.fields = {
            'publicacion': { debounce: 300, minChars: 2 },
            'ciudad': { debounce: 300, minChars: 2 },
            'temas': { debounce: 300, minChars: 2 }
        };
        
        this.timers = {};
        this.init();
    }
    
    init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setup());
        } else {
            this.setup();
        }
    }
    
    setup() {
        Object.keys(this.fields).forEach(fieldName => {
            const input = document.querySelector(`input[name="${fieldName}"]`);
            if (!input || input.list) return; // Skip si ya tiene datalist
            
            // Crear dropdown para sugerencias
            const dropdown = this.createDropdown(fieldName);
            input.parentElement.appendChild(dropdown);
            
            // Eventos
            input.addEventListener('input', (e) => this.handleInput(e, fieldName));
            input.addEventListener('focus', (e) => this.handleInput(e, fieldName));
            input.addEventListener('blur', () => {
                // Cerrar dropdown con delay para permitir clicks
                setTimeout(() => dropdown.classList.remove('show'), 200);
            });
        });
    }
    
    createDropdown(fieldName) {
        const dropdown = document.createElement('div');
        dropdown.className = 'smart-autocomplete-dropdown';
        dropdown.dataset.field = fieldName;
        return dropdown;
    }
    
    handleInput(e, fieldName) {
        const input = e.target;
        const value = input.value.trim();
        const config = this.fields[fieldName];
        
        // Clear previous timer
        clearTimeout(this.timers[fieldName]);
        
        if (value.length < config.minChars) {
            this.hideDropdown(fieldName);
            return;
        }
        
        // Debounce
        this.timers[fieldName] = setTimeout(() => {
            this.fetchSuggestions(fieldName, value);
        }, config.debounce);
    }
    
    async fetchSuggestions(fieldName, query) {
        try {
            const response = await fetch(`/api/autocomplete/${fieldName}?q=${encodeURIComponent(query)}&limit=10`);
            if (!response.ok) return;
            
            const suggestions = await response.json();
            this.showSuggestions(fieldName, suggestions);
            
        } catch (error) {
            console.error('Error fetching suggestions:', error);
        }
    }
    
    showSuggestions(fieldName, suggestions) {
        const dropdown = document.querySelector(`.smart-autocomplete-dropdown[data-field="${fieldName}"]`);
        if (!dropdown) return;
        
        if (!suggestions || suggestions.length === 0) {
            this.hideDropdown(fieldName);
            return;
        }
        
        // Construir items
        dropdown.innerHTML = suggestions.map(item => `
            <div class="autocomplete-item" data-value="${this.escapeHtml(item.value)}">
                <span class="item-value">${this.highlightMatch(item.value, fieldName)}</span>
                <span class="item-count">${item.count}</span>
            </div>
        `).join('');
        
        // Eventos click
        dropdown.querySelectorAll('.autocomplete-item').forEach(item => {
            item.addEventListener('click', () => {
                const value = item.dataset.value;
                const input = document.querySelector(`input[name="${fieldName}"]`);
                input.value = value;
                input.dispatchEvent(new Event('change'));
                this.hideDropdown(fieldName);
            });
        });
        
        dropdown.classList.add('show');
    }
    
    hideDropdown(fieldName) {
        const dropdown = document.querySelector(`.smart-autocomplete-dropdown[data-field="${fieldName}"]`);
        if (dropdown) {
            dropdown.classList.remove('show');
        }
    }
    
    highlightMatch(text, fieldName) {
        const input = document.querySelector(`input[name="${fieldName}"]`);
        if (!input) return text;
        
        const query = input.value.trim();
        if (!query) return text;
        
        const regex = new RegExp(`(${query})`, 'gi');
        return text.replace(regex, '<strong>$1</strong>');
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Inicializar
const smartAutocomplete = new SmartAutocomplete();
