const USERS_KEY = 'autoflow_users';
const CURRENT_USER_KEY = 'autoflow_current_user';

// Initial dummy user if none exists
const getStoredUsers = () => {
  const users = localStorage.getItem(USERS_KEY);
  if (!users) {
    const defaultUsers = [
      { id: '1', name: 'Demo User', email: 'demo@autoflow.ai', password: 'password123' }
    ];
    localStorage.setItem(USERS_KEY, JSON.stringify(defaultUsers));
    return defaultUsers;
  }
  return JSON.parse(users);
};

export const authApi = {
  login: async (email, password) => {
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        const users = getStoredUsers();
        const user = users.find(u => u.email === email && u.password === password);
        
        if (user) {
          const { password, ...userWithoutPassword } = user;
          localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(userWithoutPassword));
          resolve({
            user: userWithoutPassword,
            token: `mock-jwt-token-for-${userWithoutPassword.id}`
          });
        } else {
          // Check if email matches but password incorrect
          const emailExists = users.some(u => u.email === email);
          if (emailExists) {
            reject(new Error('Invalid password. Try "password123" for demo.'));
          } else {
            reject(new Error('User not found. Try demo@autoflow.ai / password123 or sign up.'));
          }
        }
      }, 700);
    });
  },

  signup: async (name, email, password) => {
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        const users = getStoredUsers();
        
        if (users.some(u => u.email === email)) {
          reject(new Error('Email is already registered.'));
          return;
        }

        const newUser = {
          id: String(users.length + 1),
          name,
          email,
          password
        };

        const updatedUsers = [...users, newUser];
        localStorage.setItem(USERS_KEY, JSON.stringify(updatedUsers));

        const { password: _, ...userWithoutPassword } = newUser;
        localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(userWithoutPassword));

        resolve({
          user: userWithoutPassword,
          token: `mock-jwt-token-for-${newUser.id}`
        });
      }, 800);
    });
  },

  logout: async () => {
    return new Promise((resolve) => {
      setTimeout(() => {
        localStorage.removeItem(CURRENT_USER_KEY);
        resolve();
      }, 300);
    });
  },

  getCurrentUser: async () => {
    const user = localStorage.getItem(CURRENT_USER_KEY);
    return user ? JSON.parse(user) : null;
  }
};
