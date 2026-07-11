/**
 * SEO & GEO Analyzer — Client-side JavaScript
 * Handles: loading states, score animations, HTMX events
 */
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('analyze-form');
    const loading = document.getElementById('loading');
    const resultContainer = document.getElementById('result-container');
    const urlInput = document.getElementById('url-input');

    // Client-side URL validation
    if (form) {
        form.addEventListener('submit', (e) => {
            const url = urlInput.value.trim();
            if (!url) {
                e.preventDefault();
                urlInput.focus();
                return;
            }
        });
    }

    // HTMX event: before request — show loading skeleton
    document.body.addEventListener('htmx:beforeRequest', (e) => {
        if (loading) {
            loading.classList.add('is-visible');
        }
        if (resultContainer) {
            resultContainer.innerHTML = '';
        }
    });

    // HTMX event: after swap — hide loading, animate scores
    document.body.addEventListener('htmx:afterSwap', (e) => {
        if (loading) {
            loading.classList.remove('is-visible');
        }
        // Trigger score circle animations
        animateScoreCircles();
    });

    // HTMX event: request error
    document.body.addEventListener('htmx:responseError', (e) => {
        if (loading) {
            loading.classList.remove('is-visible');
        }
        if (resultContainer) {
            resultContainer.innerHTML = `
                <div class="error-card">
                    <div class="error-card__icon">⚠️</div>
                    <h3 class="error-card__title">Terjadi Kesalahan</h3>
                    <p class="error-card__message">Gagal menghubungi server. Pastikan koneksi internet stabil dan coba lagi.</p>
                </div>
            `;
        }
    });

    // HTMX event: timeout
    document.body.addEventListener('htmx:timeout', (e) => {
        if (loading) {
            loading.classList.remove('is-visible');
        }
        if (resultContainer) {
            resultContainer.innerHTML = `
                <div class="error-card">
                    <div class="error-card__icon">⏱️</div>
                    <h3 class="error-card__title">Timeout</h3>
                    <p class="error-card__message">Analisa membutuhkan waktu terlalu lama. Website target mungkin lambat merespons. Coba lagi.</p>
                </div>
            `;
        }
    });
});


/**
 * Animate SVG score circle progress indicators.
 * Uses IntersectionObserver for viewport-triggered animation.
 */
function animateScoreCircles() {
    const circles = document.querySelectorAll('.score-circle__progress');
    circles.forEach(circle => {
        const score = parseInt(circle.dataset.score || '0', 10);
        // circumference = 2 * PI * r = 2 * PI * 60 ≈ 377
        const circumference = 377;
        const offset = circumference - (circumference * score / 100);

        // Small delay for visual effect
        requestAnimationFrame(() => {
            setTimeout(() => {
                circle.style.strokeDashoffset = offset;
            }, 100);
        });
    });

    // Animate number counting
    const numberEls = document.querySelectorAll('.score-circle__number');
    numberEls.forEach(el => {
        const target = parseInt(el.dataset.target || '0', 10);
        animateNumber(el, 0, target, 1200);
    });
}


/**
 * Animate a number from start to end.
 */
function animateNumber(element, start, end, duration) {
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // Ease out cubic
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = Math.round(start + (end - start) * eased);

        element.textContent = current;

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}
