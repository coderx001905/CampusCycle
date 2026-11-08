import apiClient, { setAccessToken, clearAccessToken } from './client';

export const authApi = {
  async register(data) {
    const res = await apiClient.post('/auth/register', data);
    return res.data;
  },

  async login(credentials) {
    const res = await apiClient.post('/auth/login', credentials);
    const token = res.data?.data?.access_token;
    if (token) {
      setAccessToken(token);
    }
    return res.data;
  },

  async refresh() {
    const res = await apiClient.post('/auth/refresh');
    const token = res.data?.data?.access_token;
    if (token) {
      setAccessToken(token);
    }
    return res.data;
  },

  async logout() {
    try {
      const res = await apiClient.post('/auth/logout');
      return res.data;
    } finally {
      clearAccessToken();
    }
  },

  async getMe() {
    const res = await apiClient.get('/auth/me');
    return res.data;
  },
};

export default authApi;
