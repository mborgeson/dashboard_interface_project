/** @type {import('tailwindcss').Config} */
export default {
    darkMode: ['class'],
    content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
  	extend: {
  		colors: {
  			primary: {
  				'50': '#f0f4f8',
  				'100': '#d9e2ec',
  				'200': '#bcccdc',
  				'300': '#9fb3c8',
  				'400': '#829ab1',
  				'500': '#2A3F54',
  				'600': '#243644',
  				'700': '#1e2d3a',
  				'800': '#182430',
  				'900': '#121b26'
  			},
  			accent: {
  				'50': '#fee2e2',
  				'100': '#fecaca',
  				'500': '#E74C3C',
  				'600': '#c0392b',
  				'700': '#a93226'
  			},
  			neutral: {
  				'50': '#f9fafb',
  				'100': '#f3f4f6',
  				'200': '#e5e7eb',
  				'300': '#d1d5db',
  				'400': '#9ca3af',
  				'500': '#6b7280',
  				'600': '#4b5563',
  				'700': '#374151',
  				'800': '#1f2937',
  				'900': '#111827'
  			}
  		},
  		fontFamily: {
  			sans: [
  				'Inter',
  				'system-ui',
  				'sans-serif'
  			]
  		},
  		fontSize: {
  			'hero-stat': [
  				'2.5rem',
  				{
  					lineHeight: '1.2',
  					fontWeight: '700',
  					letterSpacing: '-0.02em'
  				}
  			],
  			'page-title': [
  				'1.875rem',
  				{
  					lineHeight: '2.25rem',
  					fontWeight: '600'
  				}
  			],
  			'section-title': [
  				'1.5rem',
  				{
  					lineHeight: '2rem',
  					fontWeight: '600'
  				}
  			],
  			'card-title': [
  				'1.125rem',
  				{
  					lineHeight: '1.75rem',
  					fontWeight: '600'
  				}
  			]
  		},
  		boxShadow: {
  			card: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
  			'card-hover': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
  		},
  		animation: {
  			'fade-in': 'fadeIn 0.3s ease-in-out',
  			'slide-in': 'slideIn 0.3s ease-in-out',
  			'accordion-down': 'accordion-down 0.2s ease-out',
  			'accordion-up': 'accordion-up 0.2s ease-out'
  		},
  		keyframes: {
  			fadeIn: {
  				'0%': {
  					opacity: '0'
  				},
  				'100%': {
  					opacity: '1'
  				}
  			},
  			slideIn: {
  				'0%': {
  					transform: 'translateY(10px)',
  					opacity: '0'
  				},
  				'100%': {
  					transform: 'translateY(0)',
  					opacity: '1'
  				}
  			},
  			'accordion-down': {
  				from: {
  					height: '0'
  				},
  				to: {
  					height: 'var(--radix-accordion-content-height)'
  				}
  			},
  			'accordion-up': {
  				from: {
  					height: 'var(--radix-accordion-content-height)'
  				},
  				to: {
  					height: '0'
  				}
  			}
  		}
  	}
  },
  plugins: [],
};
