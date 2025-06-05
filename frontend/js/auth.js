// Authentication module
window.API_BASE_URL = 'http://localhost:8000';

const auth = {
    // Store token in localStorage
    setToken(token) {
        localStorage.setItem('token', token);
    },

    // Get token from localStorage
    getToken() {
        return localStorage.getItem('token');
    },

    // Remove token from localStorage
    removeToken() {
        localStorage.removeItem('token');
    },

    // Check if user is logged in
    isLoggedIn() {
        return !!this.getToken();
    },

    // Login function
    async login(email, password) {
        try {
            const formData = new FormData();
            formData.append('username', email);
            formData.append('password', password);

            const response = await fetch(`${window.API_BASE_URL}/token`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Login failed');
            }

            const data = await response.json();
            this.setToken(data.access_token);
            return true;
        } catch (error) {
            console.error('Login error:', error);
            return false;
        }
    },

    // Register function
    async register(userData) {
        try {
            const response = await fetch(`${window.API_BASE_URL}/users/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(userData)
            });

            if (!response.ok) {
                throw new Error('Registration failed');
            }

            return await response.json();
        } catch (error) {
            console.error('Registration error:', error);
            throw error;
        }
    },

    // Get current user data
    async getCurrentUser() {
        try {
            const response = await fetch(`${window.API_BASE_URL}/users/me/`, {
                headers: {
                    'Authorization': `Bearer ${this.getToken()}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to get user data');
            }

            return await response.json();
        } catch (error) {
            console.error('Get user error:', error);
            return null;
        }
    },

    // Logout function
    logout() {
        this.removeToken();
        window.location.href = '/login.html';
    }
}; 