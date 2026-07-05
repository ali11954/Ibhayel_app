/* ============================================
   Ibn Hayel - Global JavaScript
   Lightweight Mobile-First 2026
   ============================================ */

document.addEventListener('DOMContentLoaded', function() {
    initFlashMessages();
    initDropdowns();
    initBottomNav();
    initMoreMenu();
    initTableSearch();
    initFormValidation();
    initLoadingStates();
    initLazyImages();
    highlightActiveNav();
});

/* ========== Flash Messages Auto-dismiss ========== */
function initFlashMessages() {
    var alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            var closeBtn = alert.querySelector('.btn-close');
            if (closeBtn) closeBtn.click();
        }, 4000);
    });
}

/* ========== Dropdown Menus ========== */
function initDropdowns() {
    document.addEventListener('click', function(e) {
        var container = e.target.closest('.dropdown-container');
        if (container) {
            var menu = container.querySelector('.user-dropdown');
            if (menu) {
                document.querySelectorAll('.user-dropdown').forEach(function(m) {
                    if (m !== menu) m.classList.remove('show');
                });
                menu.classList.toggle('show');
            }
        } else {
            document.querySelectorAll('.user-dropdown').forEach(function(m) {
                m.classList.remove('show');
            });
        }
    });
}

function toggleUserMenu() {
    var menu = document.getElementById('userMenu');
    if (menu) menu.classList.toggle('show');
}

/* ========== Bottom Navigation ========== */
function initBottomNav() {
    var bottomNav = document.querySelector('.bottom-nav');
    if (!bottomNav) return;

    // Hide top navbar + nav-menu on mobile via JS (CSS does this too, but backup)
    if (window.innerWidth <= 768) {
        var topNavbar = document.querySelector('.top-navbar');
        if (topNavbar) topNavbar.style.display = 'none';
    }

    // Show/hide on scroll
    var lastScroll = 0;
    window.addEventListener('scroll', debounce(function() {
        var currentScroll = window.pageYOffset;
        if (currentScroll > lastScroll && currentScroll > 100) {
            bottomNav.style.transform = 'translateY(100%)';
            bottomNav.style.transition = 'transform 0.3s ease';
        } else {
            bottomNav.style.transform = 'translateY(0)';
        }
        lastScroll = currentScroll;
    }, 100), { passive: true });
}

/* ========== More Menu (Mobile) ========== */
function initMoreMenu() {
    var moreBtn = document.querySelector('.bottom-nav-more');
    if (!moreBtn) return;

    moreBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        var panel = document.getElementById('moreMenu');
        if (panel) {
            document.querySelectorAll('.bottom-nav-more-panel').forEach(function(p) {
                if (p !== panel) p.classList.remove('show');
            });
            panel.classList.toggle('show');
        }
    });

    document.addEventListener('click', function(e) {
        if (!e.target.closest('.bottom-nav-more')) {
            document.querySelectorAll('.bottom-nav-more-panel').forEach(function(p) {
                p.classList.remove('show');
            });
        }
    });

    // Close on link click
    document.querySelectorAll('.bottom-nav-more-panel a').forEach(function(link) {
        link.addEventListener('click', function() {
            var panel = document.getElementById('moreMenu');
            if (panel) panel.classList.remove('show');
        });
    });
}

/* ========== Active Nav Highlight ========== */
function highlightActiveNav() {
    var path = window.location.pathname;
    if (path === '/') return;

    // Desktop nav
    document.querySelectorAll('.nav-menu .nav-link').forEach(function(link) {
        var href = link.getAttribute('href');
        if (href && path.startsWith(href) && href !== '/') {
            link.classList.add('active');
        }
    });

    // Bottom nav
    document.querySelectorAll('.bottom-nav-item').forEach(function(item) {
        var href = item.getAttribute('href');
        if (href && path.startsWith(href) && href !== '/') {
            item.classList.add('active');
        }
    });
}

/* ========== Tooltips ========== */
function initTooltips() {
    if (typeof bootstrap === 'undefined' || !bootstrap.Tooltip) return;
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function(el) {
        new bootstrap.Tooltip(el);
    });
}

/* ========== Form Validation ========== */
function initFormValidation() {
    document.querySelectorAll('.needs-validation').forEach(function(form) {
        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
}

/* ========== Loading States ========== */
function initLoadingStates() {
    document.querySelectorAll('form[data-loading]').forEach(function(form) {
        form.addEventListener('submit', function() {
            showLoading();
        });
    });
}

function showLoading() {
    if (document.getElementById('globalLoading')) return;
    var overlay = document.createElement('div');
    overlay.id = 'globalLoading';
    overlay.className = 'spinner-overlay';
    overlay.innerHTML = '<div class="spinner-border-custom"></div>';
    document.body.appendChild(overlay);
}

function hideLoading() {
    var overlay = document.getElementById('globalLoading');
    if (overlay) overlay.remove();
}

/* ========== Lazy Image Loading ========== */
function initLazyImages() {
    if ('loading' in HTMLImageElement.prototype) return; // native support
    var lazyImages = document.querySelectorAll('img[data-src]');
    if (!lazyImages.length) return;
    var observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            if (entry.isIntersecting) {
                var img = entry.target;
                img.src = img.dataset.src;
                img.removeAttribute('data-src');
                observer.unobserve(img);
            }
        });
    });
    lazyImages.forEach(function(img) { observer.observe(img); });
}

/* ========== Confirm Dialogs ========== */
function confirmDelete(msg) {
    return confirm(msg || 'هل أنت متأكد من عملية الحذف؟');
}

function confirmAction(msg) {
    return confirm(msg || 'هل أنت متأكد من هذا الإجراء؟');
}

/* ========== Toast Notification ========== */
function showToast(message, type) {
    type = type || 'success';
    var toast = document.createElement('div');
    var colors = { success: '#22c55e', danger: '#ef4444', warning: '#f59e0b', info: '#3b82f6' };
    toast.style.cssText = 'position:fixed;top:20px;left:50%;transform:translateX(-50%);z-index:9999;padding:12px 24px;border-radius:12px;color:white;font-weight:600;font-size:14px;box-shadow:0 10px 25px rgba(0,0,0,0.15);animation:fadeInUp 0.3s ease;background:' + (colors[type] || colors.success);
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(function() {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s ease';
        setTimeout(function() { toast.remove(); }, 300);
    }, 3000);
}

/* ========== Password Toggle ========== */
function togglePassword() {
    var input = document.getElementById('password');
    var icon = document.getElementById('toggleIcon');
    if (!input || !icon) return;
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.replace('fa-eye', 'fa-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.replace('fa-eye-slash', 'fa-eye');
    }
}

/* ========== Number Formatting ========== */
function formatNumber(num) {
    return new Intl.NumberFormat('ar-YE').format(num);
}

function formatCurrency(amount) {
    return formatNumber(Math.round(amount)) + ' ر.ي';
}

/* ========== Print Utility ========== */
function printSection(elementId) {
    var element = document.getElementById(elementId);
    if (!element) return;
    var printWindow = window.open('', '_blank');
    printWindow.document.write('<html><head><title>طباعة</title>');
    printWindow.document.write('<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">');
    printWindow.document.write('<style>@media print{body{direction:rtl;font-family:Cairo,sans-serif;}}</style>');
    printWindow.document.write('</head><body>' + element.innerHTML + '</body></html>');
    printWindow.document.close();
    printWindow.print();
}

/* ========== Copy to Clipboard ========== */
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showToast('تم النسخ بنجاح', 'success');
    }).catch(function() {
        showToast('فشل في النسخ', 'danger');
    });
}

/* ========== Table Search Filter ========== */
function filterTable(inputId, tableId) {
    var input = document.getElementById(inputId);
    var table = document.getElementById(tableId);
    if (!input || !table) return;
    input.addEventListener('keyup', debounce(function() {
        var filter = input.value.toLowerCase();
        var rows = table.querySelectorAll('tbody tr');
        rows.forEach(function(row) {
            row.style.display = row.textContent.toLowerCase().includes(filter) ? '' : 'none';
        });
    }, 200));
}

function initTableSearch() {
    var searchInputs = document.querySelectorAll('[data-filter-table]');
    searchInputs.forEach(function(input) {
        var tableId = input.getAttribute('data-filter-table');
        filterTable(input.id, tableId);
    });
}

/* ========== Debounce Utility ========== */
function debounce(func, wait) {
    var timeout;
    return function() {
        var context = this, args = arguments;
        clearTimeout(timeout);
        timeout = setTimeout(function() { func.apply(context, args); }, wait);
    };
}
