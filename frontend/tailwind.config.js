/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                'code-red': '#ff4d4d',
                'code-blue': '#4d79ff',
                'code-neutral': '#cbaacb',
                'code-assassin': '#1a1a1a',
            },
            animation: {
                'flip': 'flip 0.6s forwards',
            },
        },
    },
    plugins: [],
}
