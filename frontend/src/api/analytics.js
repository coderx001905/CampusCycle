import apiClient from './client.js';

export const analyticsApi = {
  /**
   * Get high-level summary KPIs for dashboard and analytics views.
   * Scoped to actor's college for representatives; global for platform admin.
   */
  async getSummary() {
    const res = await apiClient.get('/analytics/summary');
    return res.data;
  },

  /**
   * Get resource breakdown by category.
   */
  async getCategories() {
    const res = await apiClient.get('/analytics/categories');
    return res.data;
  },

  /**
   * Get request statistics by status, type, and fulfillment.
   */
  async getRequests() {
    const res = await apiClient.get('/analytics/requests');
    return res.data;
  },

  /**
   * Get transfer statistics by status, disputes, and quantities.
   */
  async getTransfers() {
    const res = await apiClient.get('/analytics/transfers');
    return res.data;
  },

  /**
   * Get college-level analytics and participation leaderboard.
   * Requires Platform Admin role (403 for college representatives).
   */
  async getColleges() {
    const res = await apiClient.get('/analytics/colleges');
    return res.data;
  },
};

export default analyticsApi;
