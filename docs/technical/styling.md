# Styling System

The CSS architecture uses CSS custom properties and a consistent naming convention.

> **Note:** This documentation uses `cv` as the example CSS prefix. Your project may use a different prefix configured via the copier template.

## File Structure

```
docs/stylesheets/
├── custom.css           # Main theme customizations
├── custom.js            # JavaScript functionality
└── embed.js             # Embed mode support
```

## CSS Variables

All colors and values use CSS custom properties in `:root`:

```css
:root {
    /* Colors */
    --cv-primary: #3b82f6;
    --cv-primary-rgb: 59, 130, 246;
    --cv-primary-light: #dbeafe;
    --cv-primary-dark: #2563eb;
    --cv-accent: #0ea5e9;
    --cv-text: #1e293b;
    --cv-text-secondary: #475569;
    --cv-text-tertiary: #94a3b8;
    --cv-bg: #ffffff;
    --cv-bg-secondary: #f8fafc;
    --cv-bg-tertiary: #f1f5f9;
    --cv-border: #e2e8f0;
    --cv-border-light: #f1f5f9;
}
```

### Dark Mode

Variables automatically adjust for dark mode:

```css
.dark {
    --cv-primary: #60a5fa;
    --cv-primary-rgb: 96, 165, 250;
    --cv-primary-light: rgba(59, 130, 246, 0.15);
    --cv-primary-dark: #93c5fd;
    --cv-text: #f1f5f9;
    --cv-text-secondary: #cbd5e1;
    --cv-text-tertiary: #64748b;
    --cv-bg: #0f172a;
    --cv-bg-secondary: #1e293b;
    --cv-bg-tertiary: #334155;
    --cv-border: #334155;
    --cv-border-light: #1e293b;
}
```

## Class Naming

All custom classes use the `cv-` prefix to avoid conflicts with the theme:

| Prefix | Purpose |
|--------|---------|
| `cv-primary` | Primary color variable |
| `cv-text-*` | Text color variants |
| `cv-bg-*` | Background variants |
| `cv-border-*` | Border variants |

## Typography

### Fonts

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Noto+Sans:wght@400;500;600;700&display=swap');
```

### Text Sizes

| Element | Size |
|---------|------|
| h1 | 2rem |
| h2 | 1.4rem |
| h3 | 1.1rem |
| Body text | 0.95rem |
| Code | 0.8rem |

## Responsive Design

### Tablet (< 900px)

```css
@media (max-width: 900px) {
    .typography {
        max-width: 100%;
        padding: 0 1rem;
    }
}
```

### Mobile (< 768px)

```css
@media (max-width: 768px) {
    article h1 {
        font-size: 1.5rem;
    }
    article h2 {
        font-size: 1.2rem;
    }
}
```

## Customizing

### Adding New Colors

```css
:root {
    --cv-success: #10b981;
    --cv-success-light: #d1fae5;
}

.dark {
    --cv-success-light: #065f46;
}
```

### Overriding Theme Defaults

Use `!important` sparingly to override shadcn defaults:

```css
article a {
    color: var(--cv-primary) !important;
}
```

Use existing variables for consistency throughout your customizations.

## Collapsible Content (Details/Summary)

For collapsible sections, use one of these methods to ensure markdown content is properly rendered:

### Method 1: PyMDownX Details Syntax (Recommended)

Use the `??? note` syntax for admonition-style collapsibles:

```markdown
??? note "Click to expand"
    This content is **markdown** and will be properly rendered.
    
    - Lists work
    - `code` works
    - [Links](https://example.com) work

???+ info "Expanded by default"
    Use `???+` to have the section open by default.
```

### Method 2: HTML with markdown attribute

Add `markdown="1"` to enable markdown processing inside HTML tags:

```html
<details markdown="1">
<summary>Click to expand</summary>

This content is **markdown** and will be properly rendered.

- Lists work
- `code` works
- [Links](https://example.com) work

</details>
```

### Styling

Details/summary elements are styled with:
- Summary text: `--cv-primary-dark` color
- Chevron indicator that rotates on expand
- Light background with subtle border
- Proper spacing for nested content
