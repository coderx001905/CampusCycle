import React, { useEffect, useState, useCallback } from 'react';
import { Building2, CheckCircle2, XCircle, Search, ShieldCheck, Clock, Loader2 } from 'lucide-react';
import { accountsApi } from '../../api/accounts';

export const CollegeVerificationView = ({ onShowToast }) => {
  const [colleges, setColleges] = useState([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [actioningId, setActioningId] = useState(null);

  const fetchColleges = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await accountsApi.listColleges(1, 50);
      setColleges(res?.data?.items || []);
      setTotal(res?.data?.total || 0);
    } catch (err) {
      onShowToast?.({
        type: 'error',
        title: 'Error',
        message: err.message || 'Failed to load colleges.',
      });
    } finally {
      setIsLoading(false);
    }
  }, [onShowToast]);

  useEffect(() => {
    fetchColleges();
  }, [fetchColleges]);

  const handleVerification = async (collegeId, status) => {
    setActioningId(collegeId);
    try {
      await accountsApi.verifyCollege(collegeId, status);
      onShowToast?.({
        type: 'success',
        title: 'Status Updated',
        message: `College has been successfully marked as ${status}.`,
      });
      await fetchColleges();
    } catch (err) {
      onShowToast?.({
        type: 'error',
        title: 'Verification Failed',
        message: err.response?.data?.detail || err.message || 'Failed to update verification status.',
      });
    } finally {
      setActioningId(null);
    }
  };

  const filteredColleges = colleges.filter((c) => {
    const matchesFilter = filterStatus === 'all' || c.verification_status === filterStatus;
    const matchesSearch =
      !searchQuery.trim() ||
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.city.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.contact_email.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold font-display text-slate-900 dark:text-white flex items-center gap-2.5">
            <Building2 className="w-7 h-7 text-blue-600 dark:text-blue-400" />
            College Onboarding Review
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Review institution registrations, verify eligible colleges, and maintain network integrity.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs px-3 py-1.5 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-lg font-semibold">
            {total} Registered Institutions
          </span>
        </div>
      </div>

      {/* Filters and search */}
      <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
        <div className="flex items-center gap-1.5 p-1 bg-slate-100 dark:bg-slate-800/80 rounded-xl max-w-md">
          {['all', 'pending', 'verified', 'rejected'].map((status) => (
            <button
              key={status}
              onClick={() => setFilterStatus(status)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold capitalize transition-all ${
                filterStatus === status
                  ? 'bg-white dark:bg-slate-700 text-blue-600 dark:text-blue-400 shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              {status}
            </button>
          ))}
        </div>

        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by college, city, or email..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full sm:w-72 pl-9 pr-3.5 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16 text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin mr-3 text-blue-600" />
          <span className="text-sm font-medium">Loading colleges...</span>
        </div>
      ) : filteredColleges.length === 0 ? (
        <div className="p-12 text-center bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700">
          <Building2 className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
          <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300">No colleges found</h3>
          <p className="text-xs text-slate-500 mt-1">There are no colleges matching the selected filter criteria.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredColleges.map((college) => {
            const statusConfig = {
              verified: {
                bg: 'bg-emerald-50 dark:bg-emerald-950/40',
                border: 'border-emerald-200 dark:border-emerald-800',
                text: 'text-emerald-700 dark:text-emerald-300',
                badgeBg: 'bg-emerald-100 dark:bg-emerald-900/60',
                icon: <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />,
              },
              pending: {
                bg: 'bg-amber-50 dark:bg-amber-950/40',
                border: 'border-amber-200 dark:border-amber-800',
                text: 'text-amber-700 dark:text-amber-300',
                badgeBg: 'bg-amber-100 dark:bg-amber-900/60',
                icon: <Clock className="w-4 h-4 text-amber-600 dark:text-amber-400" />,
              },
              rejected: {
                bg: 'bg-rose-50 dark:bg-rose-950/40',
                border: 'border-rose-200 dark:border-rose-800',
                text: 'text-rose-700 dark:text-rose-300',
                badgeBg: 'bg-rose-100 dark:bg-rose-900/60',
                icon: <XCircle className="w-4 h-4 text-rose-600 dark:text-rose-400" />,
              },
            }[college.verification_status] || {
              bg: 'bg-slate-50',
              border: 'border-slate-200',
              text: 'text-slate-700',
              badgeBg: 'bg-slate-200',
              icon: null,
            };

            return (
              <div
                key={college.id}
                className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <h3 className="font-bold text-slate-900 dark:text-white text-base leading-snug">
                      {college.name}
                    </h3>
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold capitalize shrink-0 ${statusConfig.badgeBg} ${statusConfig.text}`}
                    >
                      {statusConfig.icon}
                      {college.verification_status}
                    </span>
                  </div>

                  <div className="space-y-1.5 text-xs text-slate-600 dark:text-slate-300">
                    <p><span className="font-medium text-slate-400">City:</span> {college.city}</p>
                    <p><span className="font-medium text-slate-400">Email:</span> {college.contact_email}</p>
                    <p className="line-clamp-2"><span className="font-medium text-slate-400">Address:</span> {college.address}</p>
                  </div>
                </div>

                <div className="mt-5 pt-4 border-t border-slate-100 dark:border-slate-700/80 flex items-center gap-2">
                  {college.verification_status !== 'verified' && (
                    <button
                      onClick={() => handleVerification(college.id, 'verified')}
                      disabled={actioningId === college.id}
                      className="flex-1 py-2 px-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold shadow-sm transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Verify</span>
                    </button>
                  )}
                  {college.verification_status !== 'rejected' && (
                    <button
                      onClick={() => handleVerification(college.id, 'rejected')}
                      disabled={actioningId === college.id}
                      className="flex-1 py-2 px-3 bg-slate-100 dark:bg-slate-700 hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-900/30 dark:hover:text-rose-400 text-slate-700 dark:text-slate-300 rounded-xl text-xs font-semibold transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      <span>Reject</span>
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default CollegeVerificationView;
