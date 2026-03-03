/**
 * Kvarplata Landing Page - Interactive Scripts
 */

// DOM Content Loaded
document.addEventListener('DOMContentLoaded', function() {
    initSmoothScroll();
    initHeaderScroll();
    initServiceCards();
    initContactForm();
    initAnimations();
});

/**
 * Smooth scroll for anchor links
 */
function initSmoothScroll() {
    const links = document.querySelectorAll('a[href^="#"]');
    
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            
            // Skip if href is just "#"
            if (href === '#') return;
            
            const target = document.querySelector(href);
            
            if (target) {
                e.preventDefault();
                
                const headerOffset = 80;
                const elementPosition = target.getBoundingClientRect().top;
                const offsetPosition = elementPosition + window.pageYOffset - headerOffset;
                
                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });
}

/**
 * Header scroll effect
 */
function initHeaderScroll() {
    const header = document.querySelector('.header');
    
    if (!header) return;
    
    let lastScrollY = window.scrollY;
    
    window.addEventListener('scroll', function() {
        const currentScrollY = window.scrollY;
        
        if (currentScrollY > 100) {
            header.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1)';
        } else {
            header.style.boxShadow = 'none';
        }
        
        lastScrollY = currentScrollY;
    });
}

/**
 * Service cards click effect
 */
function initServiceCards() {
    const cards = document.querySelectorAll('.service-card');
    
    cards.forEach(card => {
        card.addEventListener('click', function() {
            const link = this.querySelector('.service-link');
            if (link) {
                link.click();
            }
        });
        
        // Add ripple effect on click
        card.addEventListener('click', function(e) {
            const rect = this.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const ripple = document.createElement('span');
            ripple.style.position = 'absolute';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.style.width = '0px';
            ripple.style.height = '0px';
            ripple.style.borderRadius = '50%';
            ripple.style.background = 'rgba(37, 99, 235, 0.3)';
            ripple.style.transform = 'translate(-50%, -50%)';
            ripple.style.pointerEvents = 'none';
            ripple.style.transition = 'width 0.6s, height 0.6s, opacity 0.6s';
            ripple.style.opacity = '0.5';
            
            this.style.position = 'relative';
            this.style.overflow = 'hidden';
            
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.style.width = rect.width + 'px';
                ripple.style.height = rect.height + 'px';
                ripple.style.opacity = '0';
            }, 10);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });
}

/**
 * Contact form validation and submission
 */
function initContactForm() {
    const form = document.querySelector('.contact-form');
    
    if (!form) return;
    
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Basic validation
        const inputs = form.querySelectorAll('input[required], textarea[required]');
        let isValid = true;
        let emptyField = '';
        
        inputs.forEach(input => {
            if (!input.value.trim()) {
                isValid = false;
                emptyField = input.getAttribute('name');
            }
            
            // Remove error state
            input.classList.remove('error');
            const error = input.parentElement.querySelector('.error-message');
            if (error) error.remove();
        });
        
        if (!isValid) {
            alert('Пожалуйста, заполните все обязательные поля');
            return;
        }
        
        // Show success message
        const submitBtn = form.querySelector('.btn-primary');
        const originalText = submitBtn.textContent;
        
        submitBtn.textContent = 'Отправка...';
        submitBtn.disabled = true;
        
        // Simulate form submission
        setTimeout(() => {
            form.reset();
            
            // Show success message
            const successMessage = document.createElement('div');
            successMessage.className = 'success-message';
            successMessage.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: #10b981;
                color: white;
                padding: 1rem 1.5rem;
                border-radius: 0.5rem;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                z-index: 10000;
                animation: slideInRight 0.3s ease-out;
            `;
            successMessage.innerHTML = `
                <i class="fas fa-check-circle"></i>
                <span>Ваше сообщение отправлено! Мы свяжемся с вами в ближайшее время.</span>
            `;
            
            document.body.appendChild(successMessage);
            
            // Remove success message after 5 seconds
            setTimeout(() => {
                successMessage.style.animation = 'slideOutRight 0.3s ease-out';
                setTimeout(() => {
                    successMessage.remove();
                }, 300);
            }, 5000);
            
            // Reset button
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }, 1500);
    });
}

/**
 * Scroll animations
 */
function initAnimations() {
    const animatedElements = document.querySelectorAll(
        '.service-card, .feature-item, .step, .about-text'
    );
    
    const observerOptions = {
        root: null,
        rootMargin: '0px',
        threshold: 0.1
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);
    
    animatedElements.forEach(element => {
        element.style.opacity = '0';
        element.style.transform = 'translateY(30px)';
        element.style.transition = 'opacity 0.6s ease-out, transform 0.6s ease-out';
        observer.observe(element);
    });
}

/**
 * Counter animation for stats
 */
function animateCounter(element, target, duration = 2000) {
    const start = 0;
    const increment = target / (duration / 16);
    let current = start;
    
    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            current = target;
            clearInterval(timer);
        }
        element.textContent = Math.floor(current).toLocaleString();
    }, 16);
}

/**
 * Initialize counter animations when stats are visible
 */
function initCounters() {
    const counters = document.querySelectorAll('.stat-number');
    
    const counterObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const element = entry.target;
                const target = parseInt(element.getAttribute('data-target') || element.textContent.replace(/\D/g, ''));
                
                // Reset and restart animation
                element.textContent = '0';
                element.style.transition = 'none';
                
                // Force reflow
                element.offsetHeight;
                
                animateCounter(element, target);
                
                counterObserver.unobserve(element);
            }
        });
    }, { threshold: 0.5 });
    
    counters.forEach(counter => {
        counterObserver.observe(counter);
    });
}

// Initialize counters after a short delay
setTimeout(initCounters, 500);

/**
 * Mobile menu toggle (if needed in future)
 */
function initMobileMenu() {
    const menuBtn = document.querySelector('.mobile-menu-btn');
    const nav = document.querySelector('.nav');
    
    if (!menuBtn || !nav) return;
    
    menuBtn.addEventListener('click', function() {
        nav.classList.toggle('active');
        menuBtn.classList.toggle('active');
    });
}

// Initialize mobile menu if elements exist
setTimeout(initMobileMenu, 100);

/**
 * Add CSS animations dynamically
 */
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .service-card {
        transition: transform 0.3s ease, box-shadow 0.3s ease, border-color 0.3s ease;
    }
    
    .feature-item,
    .step,
    .about-text {
        transition: opacity 0.6s ease-out, transform 0.6s ease-out;
    }
`;
document.head.appendChild(style);

/**
 * Console branding
 */
console.log('%c🌐 Kvarplata Landing Page', 'font-size: 16px; font-weight: bold; color: #2563eb;');
console.log('%cВсе сервисы работают стабильно и надежно', 'font-size: 12px; color: #10b981;');
