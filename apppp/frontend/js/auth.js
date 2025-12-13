
// Ensure api.js is loaded before this file
// Or use ES6 modules if we change setup, but for now simple script tags

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');

    // Login Handler
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const submitBtn = loginForm.querySelector('button[type="submit"]');

            try {
                submitBtn.disabled = true;
                submitBtn.innerText = 'Signing In...';

                const data = await api.post('/auth/login', { email, password });

                localStorage.setItem('auth_token', data.token);
                localStorage.setItem('user', JSON.stringify(data.user)); // Basic user info

                window.location.href = 'dashboard.html';
            } catch (error) {
                alert(error.message);
                submitBtn.disabled = false;
                submitBtn.innerText = 'Sign In';
            }
        });
    }

    // Register Handler
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const fullName = document.getElementById('fullName').value;
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirmPassword').value;
            const submitBtn = registerForm.querySelector('button[type="submit"]');

            if (password !== confirmPassword) {
                alert("Passwords do not match!");
                return;
            }

            try {
                submitBtn.disabled = true;
                submitBtn.innerText = 'Creating Account...';

                const data = await api.post('/auth/register', { email, password, fullName });

                alert('Account created! Please check your email to verify.');
                window.location.href = 'login.html';
            } catch (error) {
                alert(error.message);
                submitBtn.disabled = false;
                submitBtn.innerText = 'Create Account';
            }
        });
    }
});
