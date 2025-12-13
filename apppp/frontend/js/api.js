
const API_URL = 'http://localhost:5000/api';

const api = {
    async post(endpoint, data) {
        const headers = { 'Content-Type': 'application/json' };
        const token = localStorage.getItem('auth_token');
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const response = await fetch(`${API_URL}${endpoint}`, {
            method: 'POST',
            headers,
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Something went wrong');
        }

        return response.json();
    },

    async get(endpoint) {
        const headers = { 'Content-Type': 'application/json' };
        const token = localStorage.getItem('auth_token');
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const response = await fetch(`${API_URL}${endpoint}`, {
            method: 'GET',
            headers
        });

        if (!response.ok) {
            if (response.status === 401) {
                // Auto logout on 401
                localStorage.removeItem('auth_token');
                window.location.href = 'login.html';
            }
            throw new Error('Request failed');
        }

        return response.json();
    }
};
