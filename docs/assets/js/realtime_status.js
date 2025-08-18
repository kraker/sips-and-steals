/**
 * Real-Time Happy Hour Status Logic
 * 
 * Provides functions to determine current happy hour status,
 * next upcoming deals, and time-aware filtering for the dashboard.
 */

class HappyHourStatus {
    constructor() {
        this.currentTime = new Date();
        this.currentDay = this.getCurrentDayName();
        this.currentHour = this.currentTime.getHours();
        this.currentMinute = this.currentTime.getMinutes();
    }

    getCurrentDayName() {
        const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        return days[this.currentTime.getDay()];
    }

    isWeekday() {
        const weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
        return weekdays.includes(this.currentDay);
    }

    isWeekend() {
        return ['Saturday', 'Sunday'].includes(this.currentDay);
    }

    parseTimeString(timeStr) {
        /**
         * Parse time strings like "3:00 PM", "5:30 PM", etc.
         * Returns 24-hour format for comparison
         */
        if (!timeStr) return null;

        const timeMatch = timeStr.match(/(\d{1,2}):(\d{2})\s*(AM|PM)/i);
        if (!timeMatch) return null;

        let hour = parseInt(timeMatch[1]);
        const minute = parseInt(timeMatch[2]);
        const period = timeMatch[3].toUpperCase();

        if (period === 'PM' && hour !== 12) {
            hour += 12;
        } else if (period === 'AM' && hour === 12) {
            hour = 0;
        }

        return { hour, minute };
    }

    parseTimeRange(timeRange) {
        /**
         * Parse time ranges like "3:00 PM - 6:00 PM"
         * Returns start and end times
         */
        if (!timeRange || timeRange === 'All Day') {
            return { start: { hour: 0, minute: 0 }, end: { hour: 23, minute: 59 } };
        }

        const rangeParts = timeRange.split(' - ');
        if (rangeParts.length !== 2) return null;

        const start = this.parseTimeString(rangeParts[0].trim());
        const end = this.parseTimeString(rangeParts[1].trim());

        if (!start || !end) return null;

        return { start, end };
    }

    isCurrentlyInTimeRange(timeRange) {
        /**
         * Check if current time falls within the given range
         */
        const range = this.parseTimeRange(timeRange);
        if (!range) return false;

        const currentMinutes = this.currentHour * 60 + this.currentMinute;
        const startMinutes = range.start.hour * 60 + range.start.minute;
        const endMinutes = range.end.hour * 60 + range.end.minute;

        // Handle overnight ranges (like 9 PM - 2 AM)
        if (endMinutes < startMinutes) {
            return currentMinutes >= startMinutes || currentMinutes <= endMinutes;
        }

        return currentMinutes >= startMinutes && currentMinutes <= endMinutes;
    }

    isDayActive(daysList) {
        /**
         * Check if current day matches any in the restaurant's schedule
         */
        if (!daysList || daysList.length === 0) return false;

        for (const day of daysList) {
            if (day === 'Daily') return true;
            if (day === 'Weekdays' && this.isWeekday()) return true;
            if (day === 'Weekends' && this.isWeekend()) return true;
            if (day === this.currentDay) return true;
        }

        return false;
    }

    getHappyHourStatus(restaurant) {
        /**
         * Get comprehensive status for a restaurant
         * Returns: 'active', 'upcoming', 'closed', 'unknown'
         */
        const schedule = restaurant.happy_hour?.weekly_schedule;
        if (!schedule || schedule.length === 0) {
            return {
                status: 'unknown',
                message: 'Check restaurant for happy hour details',
                nextTime: null
            };
        }

        let isActive = false;
        let nextHappyHour = null;
        let statusMessage = '';

        for (const period of schedule) {
            const daysActive = this.isDayActive(period.days);
            
            if (daysActive && period.times) {
                for (const timeRange of period.times) {
                    if (this.isCurrentlyInTimeRange(timeRange)) {
                        isActive = true;
                        statusMessage = `Happy hour until ${timeRange.split(' - ')[1]}`;
                        break;
                    }
                    
                    // Check for upcoming happy hour today
                    const range = this.parseTimeRange(timeRange);
                    if (range) {
                        const startMinutes = range.start.hour * 60 + range.start.minute;
                        const currentMinutes = this.currentHour * 60 + this.currentMinute;
                        
                        if (startMinutes > currentMinutes) {
                            const hoursUntil = Math.floor((startMinutes - currentMinutes) / 60);
                            const minutesUntil = (startMinutes - currentMinutes) % 60;
                            
                            if (hoursUntil === 0) {
                                nextHappyHour = `Starts in ${minutesUntil} minutes`;
                            } else if (hoursUntil <= 2) {
                                nextHappyHour = `Starts in ${hoursUntil}h ${minutesUntil}m`;
                            }
                        }
                    }
                }
            }
        }

        if (isActive) {
            return {
                status: 'active',
                message: statusMessage,
                nextTime: null
            };
        } else if (nextHappyHour) {
            return {
                status: 'upcoming',
                message: nextHappyHour,
                nextTime: nextHappyHour
            };
        } else {
            return {
                status: 'closed',
                message: 'No current happy hour',
                nextTime: null
            };
        }
    }

    getStatusIcon(status) {
        /**
         * Get emoji/icon for status
         */
        switch (status) {
            case 'active': return '🟢';
            case 'upcoming': return '🟡';
            case 'closed': return '🔴';
            default: return '⚪';
        }
    }

    getStatusClass(status) {
        /**
         * Get CSS class for status styling
         */
        switch (status) {
            case 'active': return 'status-active';
            case 'upcoming': return 'status-upcoming';
            case 'closed': return 'status-closed';
            default: return 'status-unknown';
        }
    }

    formatCurrentTime() {
        /**
         * Format current time for display
         */
        return this.currentTime.toLocaleString('en-US', {
            weekday: 'long',
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        });
    }

    filterRestaurantsByStatus(restaurants, filterType = 'all') {
        /**
         * Filter restaurants by their current status
         * filterType: 'active', 'upcoming', 'all'
         */
        const filtered = {};
        
        for (const [slug, restaurant] of Object.entries(restaurants)) {
            const status = this.getHappyHourStatus(restaurant);
            
            if (filterType === 'all' || 
                filterType === status.status ||
                (filterType === 'soon' && ['active', 'upcoming'].includes(status.status))) {
                
                // Add status info to restaurant data
                filtered[slug] = {
                    ...restaurant,
                    currentStatus: status
                };
            }
        }
        
        return filtered;
    }

    sortByStatus(restaurants) {
        /**
         * Sort restaurants by status priority (active first, then upcoming, then closed)
         */
        const statusPriority = { 'active': 1, 'upcoming': 2, 'closed': 3, 'unknown': 4 };
        
        return Object.entries(restaurants).sort(([, a], [, b]) => {
            const aPriority = statusPriority[a.currentStatus?.status] || 4;
            const bPriority = statusPriority[b.currentStatus?.status] || 4;
            return aPriority - bPriority;
        });
    }

    getDistrictSummary(restaurants) {
        /**
         * Get summary stats for the district
         */
        let activeCount = 0;
        let upcomingCount = 0;
        let totalCount = Object.keys(restaurants).length;

        for (const restaurant of Object.values(restaurants)) {
            const status = this.getHappyHourStatus(restaurant);
            if (status.status === 'active') activeCount++;
            if (status.status === 'upcoming') upcomingCount++;
        }

        return {
            total: totalCount,
            active: activeCount,
            upcoming: upcomingCount,
            message: activeCount > 0 ? 
                `${activeCount} happy hours active now` : 
                upcomingCount > 0 ? 
                    `${upcomingCount} starting soon` : 
                    'No active happy hours'
        };
    }
}

// Export for use in dashboard
if (typeof module !== 'undefined' && module.exports) {
    module.exports = HappyHourStatus;
}