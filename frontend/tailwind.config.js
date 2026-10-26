/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/app/**/*.{ts,tsx}', './src/components/workspace/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: '#F7F7F8',
        surface: '#FFFFFF',
        ink: {
          DEFAULT: '#171717',
          muted: '#737373',
        },
        lime: {
          DEFAULT: '#E6FF45',
          hover: '#d8f32c',
          soft: '#F7FFD1',
        },
        ai: {
          DEFAULT: '#8B6AF5',
          hover: '#7955eb',
          soft: '#F1EDFE',
        },
        nav: '#111111',
        border: '#E5E7EB',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 3px 0 rgba(0, 0, 0, 0.04), 0 1px 2px -1px rgba(0, 0, 0, 0.04)',
        floating: '0 20px 35px -10px rgba(17, 17, 17, 0.12), 0 4px 12px -2px rgba(17, 17, 17, 0.06)',
      },
    },
  },
  plugins: [],
};
