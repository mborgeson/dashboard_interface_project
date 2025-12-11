# Toast Notifications - Visual Reference

## Toast Components Preview

### Success Toast
```
┌─────────────────────────────────────┐
│ ✓  Property saved successfully   ✕ │
├─────────────────────────────────────┤
│ ████████████████████████░░░░░░░░░░ │ ← Progress bar
└─────────────────────────────────────┘
Color: Green (green-500/green-100)
Icon: CheckCircle
```

### Error Toast with Description
```
┌─────────────────────────────────────┐
│ ✕  Upload failed                 ✕ │
│    File size exceeds 10MB limit     │
├─────────────────────────────────────┤
│ ████████████████░░░░░░░░░░░░░░░░░░ │
└─────────────────────────────────────┘
Color: Red (red-500/red-100)
Icon: XCircle
```

### Warning Toast with Action
```
┌─────────────────────────────────────┐
│ ⚠  Unsaved changes               ✕ │
│    You have unsaved changes         │
│    [View Changes →]                 │
├─────────────────────────────────────┤
│ ███████████░░░░░░░░░░░░░░░░░░░░░░░ │
└─────────────────────────────────────┘
Color: Amber (amber-500/amber-100)
Icon: AlertTriangle
```

### Info Toast
```
┌─────────────────────────────────────┐
│ ℹ  New feature available         ✕ │
│    Check out the analytics panel    │
├─────────────────────────────────────�┤
│ ██████████████████████████████████ │
└─────────────────────────────────────┘
Color: Blue (blue-500/blue-100)
Icon: Info
```

### Multiple Toasts Stack
```
Position: Fixed bottom-right
Stacking: Vertical with gap-2
Maximum: 5 visible toasts
Overflow: Older toasts removed

                    ┌─────────────────┐
                    │ Toast 5 (newest)│
                    └─────────────────┘
                    ┌─────────────────┐
                    │ Toast 4         │
                    └─────────────────┘
                    ┌─────────────────┐
                    │ Toast 3         │
                    └─────────────────┘
                    ┌─────────────────┐
                    │ Toast 2         │
                    └─────────────────┘
                    ┌─────────────────┐
                    │ Toast 1 (oldest)│
                    └─────────────────┘
```

## Alert Banner Components

### Info Banner
```
┌──────────────────────────────────────────────────────────────┐
│ ℹ  New features available                                 ✕ │
│    We've added new analytics features to track performance.  │
│    [Learn More →]                                            │
└──────────────────────────────────────────────────────────────┘
Full-width, Blue background
```

### Success Banner
```
┌──────────────────────────────────────────────────────────────┐
│ ✓  Property successfully saved                               │
│    All changes have been saved to your portfolio.            │
└──────────────────────────────────────────────────────────────┘
Full-width, Green background
```

### Warning Banner
```
┌──────────────────────────────────────────────────────────────┐
│ ⚠  Payment method expiring soon                           ✕ │
│    Your credit card ending in 4242 expires next month.       │
│    [Update Payment →]                                        │
└──────────────────────────────────────────────────────────────┘
Full-width, Amber background
```

### Error Banner
```
┌──────────────────────────────────────────────────────────────┐
│ ✕  Document upload failed                                 ✕ │
│    The file could not be uploaded. Please contact support.  │
│    [Retry →]                                                 │
└──────────────────────────────────────────────────────────────┘
Full-width, Red background
```

## Animation Behavior

### Toast Entrance
```
Frame 1: [off-screen right] →
Frame 2:                  → [sliding in]
Frame 3:                            → [in position]

Duration: 300ms
Easing: ease-out
Transform: translateX(100%) → translateX(0)
Opacity: 0 → 1
```

### Toast Exit
```
Frame 1: [in position]
Frame 2: [sliding out] →
Frame 3:              → [off-screen right]

Duration: 300ms
Easing: ease-in
Transform: translateX(0) → translateX(100%)
Opacity: 1 → 0
```

### Progress Bar
```
Start: ████████████████████████████████████ 100%
  ↓    (animation over toast.duration)
End:   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 0%

Updates: ~60fps (every 16ms)
Animation: linear
```

## Color Specifications

### Light Mode
```css
Success:
  Background: bg-green-50
  Border: border-green-500 (left border-l-4)
  Icon: text-green-500
  Text: text-green-900
  Progress: bg-green-500

Error:
  Background: bg-red-50
  Border: border-red-500
  Icon: text-red-500
  Text: text-red-900
  Progress: bg-red-500

Warning:
  Background: bg-amber-50
  Border: border-amber-500
  Icon: text-amber-500
  Text: text-amber-900
  Progress: bg-amber-500

Info:
  Background: bg-blue-50
  Border: border-blue-500
  Icon: text-blue-500
  Text: text-blue-900
  Progress: bg-blue-500
```

### Dark Mode
```css
Success:
  Background: dark:bg-green-950
  Border: border-green-500
  Icon: text-green-500
  Text: dark:text-green-100
  Progress: bg-green-500

Error:
  Background: dark:bg-red-950
  Border: border-red-500
  Icon: text-red-500
  Text: dark:text-red-100
  Progress: bg-red-500

Warning:
  Background: dark:bg-amber-950
  Border: border-amber-500
  Icon: text-amber-500
  Text: dark:text-amber-100
  Progress: bg-amber-500

Info:
  Background: dark:bg-blue-950
  Border: border-blue-500
  Icon: text-blue-500
  Text: dark:text-blue-100
  Progress: bg-blue-500
```

## Layout Specifications

### Toast Dimensions
```
Width: 24rem (384px / w-96)
Max-width: 100vw - 2rem (responsive)
Min-height: 72px (variable based on content)
Border-radius: 0.5rem (rounded-lg)
Border-left: 4px solid (border-l-4)
Shadow: shadow-lg
Padding: 1rem (p-4)
```

### Toast Container
```
Position: fixed
Bottom: 1rem (bottom-4)
Right: 1rem (right-4)
Z-index: 9999
Gap: 0.5rem (gap-2)
Flex-direction: column
Pointer-events: none (children: auto)
```

### Alert Banner Dimensions
```
Width: 100% (w-full)
Padding: 1rem (p-4)
Border-radius: 0.5rem (rounded-lg)
Border: 1px solid (border)
```

## Icon Set

### Lucide React Icons
```typescript
import {
  CheckCircle,    // Success ✓
  XCircle,        // Error ✕
  AlertTriangle,  // Warning ⚠
  Info,           // Info ℹ
  X              // Close button ✕
} from 'lucide-react';
```

### Icon Sizes
```
Toast icons: h-5 w-5 (20px)
Close button icon: h-4 w-4 (16px)
```

## Accessibility

### ARIA Attributes
```html
<!-- Toast Container -->
<div
  aria-live="polite"
  aria-atomic="false"
>

<!-- Toast Component -->
<button aria-label="Close notification">

<!-- Alert Banner -->
<div role="alert">
<button aria-label="Dismiss alert">
```

### Keyboard Navigation
```
Tab: Focus close button
Enter/Space: Trigger close/action
Escape: Could dismiss (optional enhancement)
```

## Z-Index Hierarchy
```
Level 10: Modals/Dialogs (9999+)
Level 9:  Toast Container (9999) ← Toast system
Level 8:  Dropdowns/Tooltips (9998)
Level 7:  Fixed Navigation (100)
Level 1:  Base Content (1)
```

## Responsive Behavior

### Mobile (<768px)
```
Toast width: calc(100vw - 2rem)
Position: bottom-4 right-4
Max toasts visible: 3 (reduced from 5)
```

### Tablet (768px - 1024px)
```
Toast width: 24rem
Position: bottom-4 right-4
Max toasts visible: 4
```

### Desktop (>1024px)
```
Toast width: 24rem
Position: bottom-4 right-4
Max toasts visible: 5
```

## Performance Characteristics

### Rendering
```
Initial render: <16ms (60fps)
Animation frame: ~16ms (60fps target)
State update: <5ms
Portal mount: <10ms
```

### Memory
```
Toast store size: ~1KB per toast
Max memory: ~5KB (5 toasts)
Cleanup: Automatic on dismiss
GC: Timers cleared on unmount
```

### Timing Defaults
```
Default duration: 5000ms (5 seconds)
Animation duration: 300ms
Progress update interval: 16ms (~60fps)
```
