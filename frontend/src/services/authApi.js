const USERS_KEY = 'autoflow_users';
const CURRENT_USER_KEY = 'autoflow_current_user';

// Retrieve stored users from localStorage
const getStoredUsers = () => {
  const users = localStorage.getItem(USERS_KEY);
  if (!users) {
    localStorage.setItem(USERS_KEY, JSON.stringify([]));
    return [];
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
            reject(new Error('Incorrect password. Please try again.'));
          } else {
            reject(new Error('No account found with this email. Please sign up.'));
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
          id: String(Date.now()),
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