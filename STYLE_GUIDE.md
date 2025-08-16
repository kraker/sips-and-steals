# Sips and Steals Style Guide

## HTML/CSS Formatting Standards

### Indentation
- **Use spaces, not tabs** for all HTML and CSS files
- **2 spaces** for each level of nesting (not 4 spaces)
- Consistent indentation throughout all template files

### HTML Templates (Jinja2)
- Use 2-space indentation for nested elements
- Jinja2 template tags should align with their containing HTML element
- Use semantic HTML5 elements where possible (following Pico CSS conventions)

### CSS
- Use 2-space indentation for nested selectors and properties
- Group related CSS rules together
- Use CSS custom properties (variables) for consistent theming

### File Organization
- `templates/base.html` - Base template with shared structure (no inline styles)
- `templates/index.html` - Main restaurant listing page
- `templates/restaurant.html` - Individual restaurant profile pages (no inline styles)
- `docs/assets/css/main.css` - Consolidated custom CSS file with all styling
- Generated files go in `docs/` directory

### Design System

#### Colors
- `--urban-accent: #ff6b35` - Primary accent color (orange)
- `--urban-secondary: #2c3e50` - Secondary color
- `--urban-text: #ecf0f1` - Primary text color
- `--urban-muted: #95a5a6` - Muted text color
- `--urban-dark: #1a1a1a` - Background color

#### Typography
- Primary font: Inter (Google Fonts)
- Font weights: 300, 400, 500, 600, 700
- Letter spacing: -0.01em for body text

#### Interactive Elements
- Buttons use Pico CSS semantic HTML approach
- Links have hover transitions (0.2s ease)
- Website links use accent color with white hover state

### Coding Standards
- **Prioritize Pico CSS native styling** over custom CSS where possible
- Use semantic HTML elements (`<button>`, `<main>`, `<section>`, `<address>`, `<details>`, `<mark>`, etc.)
- **No inline styles** - all custom CSS consolidated in `docs/assets/css/main.css`
- **Clean separation** between HTML templates and CSS styling
- Use descriptive class names following BEM-like conventions
- Include accessibility attributes where appropriate
- Leverage Pico CSS components: `<details>` for collapsible content, `<mark>` for tags, `<address>` for location info

### Example HTML Structure
```html
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}Default Title{% endblock %}</title>
</head>
<body>
  <main class="container">
    <header class="hero">
      <div class="city">Denver</div>
      <h1>Sips and Steals</h1>
    </header>
    
    {% block content %}{% endblock %}
    
    <footer>
      <p>Footer content</p>
    </footer>
  </main>
</body>
</html>
```

### Example CSS Structure
```css
.restaurant-card {
  border: 1px solid var(--pico-muted-border-color);
  border-radius: 12px;
  padding: 1.5rem;
  background: var(--pico-card-background-color);
  transition: all 0.2s ease;
}

.restaurant-card:hover {
  border-color: var(--urban-accent);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
```

## Target User Persona
**The Discerning Urban Explorer**: Sophisticated food and beverage enthusiasts who view happy hour as smart luxury, not budget dining. They appreciate quality, culinary adventure, and strategic dining experiences.