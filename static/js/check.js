// check.js

window.addEventListener('DOMContentLoaded', function () {
    if (document.querySelector('.fancy-success')) {
        const emoji = document.querySelector('.fancy-success .emoji');
        if (emoji) {
            emoji.animate([
                { transform: 'rotate(-6deg) scale(1.1)', color: '#f6c947' },
                { transform: 'rotate(5deg) scale(1.2)', color: '#a7f76e' },
                { transform: 'rotate(-2deg) scale(1.08)', color: '#f6c947' }
            ], {
                duration: 800,
                iterations: 2
            });
        }
    }
});
