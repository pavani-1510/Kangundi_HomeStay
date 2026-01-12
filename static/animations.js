// Scroll Animation Handler with Intersection Observer
document.addEventListener('DOMContentLoaded', () => {
    // Elements to animate on scroll
    const animateOnScroll = document.querySelectorAll(
        '.highlight-item, .benefit, .section-block, .final-cta'
    );

    // Create Intersection Observer
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                // Add animation classes when element enters viewport
                entry.target.style.opacity = '1';
                
                // Add extra glow effect on benefits
                if (entry.target.classList.contains('benefit')) {
                    entry.target.style.animation = `slideInLeft 0.7s cubic-bezier(0.4, 0, 0.2, 1) forwards, glow 2s ease-in-out 1s infinite`;
                }
                
                // Parallax effect on section blocks
                if (entry.target.classList.contains('section-block')) {
                    entry.target.style.opacity = '1';
                }
                
                // Stop observing once animated
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    });

    // Observe all elements
    animateOnScroll.forEach(el => {
        observer.observe(el);
    });

    // Parallax scrolling effect for background
    let ticking = false;
    window.addEventListener('scroll', () => {
        if (!ticking) {
            window.requestAnimationFrame(() => {
                const scrolled = window.pageYOffset;
                const bgElement = document.querySelector('.dashboard-page::before');
                
                // Subtle parallax effect
                const parallaxElements = document.querySelectorAll('.hero-section, .section-block');
                parallaxElements.forEach((el, index) => {
                    el.style.transform = `translateY(${scrolled * 0.05 * (index + 1)}px)`;
                });
                
                ticking = false;
            });
            ticking = true;
        }
    }, { passive: true });

    // Add smooth scroll behavior
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Button ripple effect on click
    document.querySelectorAll('.cta-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.cssText = `
                position: absolute;
                width: ${size}px;
                height: ${size}px;
                left: ${x}px;
                top: ${y}px;
                background: rgba(255, 255, 255, 0.6);
                border-radius: 50%;
                pointer-events: none;
                animation: ripple-effect 0.6s ease-out;
            `;
            
            this.style.position = 'relative';
            this.style.overflow = 'hidden';
            this.appendChild(ripple);
            
            setTimeout(() => ripple.remove(), 600);
        });
    });
});

// Ripple animation keyframe
const style = document.createElement('style');
style.textContent = `
    @keyframes ripple-effect {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
