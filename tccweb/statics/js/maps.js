/**
 * Google Maps integration for Safe Campus Platform
 * Handles location selection and display for incident reporting
 */

let map;
let marker;
let geocoder;
let autocomplete;

/**
 * Initialize Google Maps
 * Called by the Google Maps API script callback
 */
function initMap() {
    // Default center (you can customize this to your university location)
    const defaultCenter = { lat: 6.9271, lng: 79.8612 }; // Colombo, Sri Lanka
    
    // Initialize map
    map = new google.maps.Map(document.getElementById('map'), {
        zoom: 15,
        center: defaultCenter,
        mapTypeControl: false,
        fullscreenControl: false,
        streetViewControl: false,
        styles: [
            {
                featureType: 'poi',
                elementType: 'labels',
                stylers: [{ visibility: 'on' }]
            }
        ]
    });
    
    // Initialize geocoder
    geocoder = new google.maps.Geocoder();
    
    // Initialize autocomplete for location input
    const locationInput = document.getElementById('location');
    if (locationInput) {
        setupAutocomplete(locationInput);
    }
    
    // Add click listener to map
    map.addListener('click', function(event) {
        handleMapClick(event.latLng);
    });
    
    // Try to get user's current location
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            function(position) {
                const userLocation = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                };
                
                // Check if the location is within a reasonable distance (university campus)
                if (isLocationWithinCampus(userLocation)) {
                    map.setCenter(userLocation);
                    map.setZoom(17);
                    
                    // Add a subtle indicator for current location
                    new google.maps.Marker({
                        position: userLocation,
                        map: map,
                        icon: {
                            path: google.maps.SymbolPath.CIRCLE,
                            scale: 8,
                            fillColor: '#4285F4',
                            fillOpacity: 0.8,
                            strokeColor: '#ffffff',
                            strokeWeight: 2
                        },
                        title: 'Your current location'
                    });
                }
            },
            function(error) {
                console.warn('Geolocation error:', error);
            },
            {
                enableHighAccuracy: true,
                timeout: 5000,
                maximumAge: 300000
            }
        );
    }
}

// Ensure Google callback can find initMap
window.initMap = initMap;

/**
 * Setup autocomplete for location input
 * @param {HTMLInputElement} input - The location input field
 */
function setupAutocomplete(input) {
    autocomplete = new google.maps.places.Autocomplete(input, {
        fields: ['geometry', 'name', 'formatted_address'],
        types: ['establishment', 'geocode']
    });
    
    // Bias autocomplete to map viewport
    autocomplete.bindTo('bounds', map);
    
    autocomplete.addListener('place_changed', function() {
        const place = autocomplete.getPlace();
        
        if (!place.geometry || !place.geometry.location) {
            window.SafeCampus?.showNotification('No details available for input: ' + place.name, 'warning');
            return;
        }
        
        // Update map and marker
        const location = place.geometry.location;
        handleMapClick(location);
        
        // Update the input field
        input.value = place.formatted_address || place.name;
    });
}

/**
 * Handle map click events
 * @param {google.maps.LatLng} latLng - The clicked location
 */
function handleMapClick(latLng) {
    // Update marker position
    if (marker) {
        marker.setPosition(latLng);
    } else {
        marker = new google.maps.Marker({
            position: latLng,
            map: map,
            draggable: true,
            title: 'Incident Location'
        });
        
        // Add drag listener
        marker.addListener('dragend', function() {
            const position = marker.getPosition();
            updateLocationData(position);
        });
    }
    
    // Update form fields
    updateLocationData(latLng);
    
    // Reverse geocode to get address
    reverseGeocode(latLng);
    
    // Center map on the marker
    map.setCenter(latLng);
}

/**
 * Update hidden form fields with location data
 * @param {google.maps.LatLng} latLng - The location coordinates
 */
function updateLocationData(latLng) {
    const latitudeField = document.getElementById('latitude');
    const longitudeField = document.getElementById('longitude');
    
    if (latitudeField) {
        latitudeField.value = latLng.lat();
    }
    if (longitudeField) {
        longitudeField.value = latLng.lng();
    }
    
    // Announce to screen readers
    if (window.SafeCampus?.announceToScreenReader) {
        window.SafeCampus.announceToScreenReader('Location selected on map');
    }
}

/**
 * Reverse geocode coordinates to get address
 * @param {google.maps.LatLng} latLng - The coordinates to reverse geocode
 */
function reverseGeocode(latLng) {
    geocoder.geocode({ location: latLng }, function(results, status) {
        if (status === 'OK') {
            if (results[0]) {
                const locationInput = document.getElementById('location');
                if (locationInput && !locationInput.value) {
                    // Use the most specific address available
                    locationInput.value = results[0].formatted_address;
                }
                
                // Add info window to marker
                if (marker) {
                    const infoWindow = new google.maps.InfoWindow({
                        content: `
                            <div>
                                <strong>Selected Location</strong><br>
                                ${results[0].formatted_address}
                            </div>
                        `
                    });
                    
                    marker.addListener('click', function() {
                        infoWindow.open(map, marker);
                    });
                }
            }
        } else {
            console.warn('Geocoder failed due to: ' + status);
        }
    });
}

/**
 * Check if location is within campus boundaries
 * @param {Object} location - Location object with lat and lng properties
 * @returns {boolean} True if location is within campus
 */
function isLocationWithinCampus(location) {
    // Define campus boundaries (customize for your university)
    const campusBounds = {
        north: 6.935,
        south: 6.920,
        east: 79.870,
        west: 79.850
    };
    
    return (
        location.lat <= campusBounds.north &&
        location.lat >= campusBounds.south &&
        location.lng <= campusBounds.east &&
        location.lng >= campusBounds.west
    );
}

/**
 * Clear map selection
 */
function clearMapSelection() {
    if (marker) {
        marker.setMap(null);
        marker = null;
    }
    
    // Clear form fields
    const latitudeField = document.getElementById('latitude');
    const longitudeField = document.getElementById('longitude');
    
    if (latitudeField) latitudeField.value = '';
    if (longitudeField) longitudeField.value = '';
    
    if (window.SafeCampus?.announceToScreenReader) {
        window.SafeCampus.announceToScreenReader('Map selection cleared');
    }
}

/**
 * Center map on the user's current location
 */
function useCurrentLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            function(position) {
                const userLocation = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                };
                handleMapClick(userLocation);
                map.setCenter(userLocation);
                map.setZoom(17);
            },
            function(error) {
                console.warn('Geolocation error:', error);
            }
        );
    }
}

/**
 * Initialize map in modal
 * @param {number} lat - Latitude
 * @param {number} lng - Longitude
 */
function initModalMap(lat, lng) {
    const modalMap = new google.maps.Map(document.getElementById('modalMap'), {
        zoom: 16,
        center: { lat: lat, lng: lng },
        mapTypeControl: false,
        fullscreenControl: true,
        streetViewControl: true
    });
    
    // Add marker for the incident location
    new google.maps.Marker({
        position: { lat: lat, lng: lng },
        map: modalMap,
        title: 'Incident Location',
        icon: {
            path: google.maps.SymbolPath.CIRCLE,
            scale: 10,
            fillColor: '#dc3545',
            fillOpacity: 0.8,
            strokeColor: '#ffffff',
            strokeWeight: 2
        }
    });
    
    // Add info window
    const infoWindow = new google.maps.InfoWindow({
        content: '<div><strong>Reported Incident Location</strong></div>',
        position: { lat: lat, lng: lng }
    });
    
    infoWindow.open(modalMap);
}

/**
 * Get user-friendly location description
 * @param {number} lat - Latitude
 * @param {number} lng - Longitude
 * @param {Function} callback - Callback function to receive the description
 */
function getLocationDescription(lat, lng, callback) {
    const latLng = new google.maps.LatLng(lat, lng);
    
    geocoder.geocode({ location: latLng }, function(results, status) {
        if (status === 'OK' && results[0]) {
            // Try to get a more specific description
            const addressComponents = results[0].address_components;
            let description = results[0].formatted_address;
            
            // Look for establishment or point of interest
            for (let component of addressComponents) {
                if (component.types.includes('establishment') || 
                    component.types.includes('point_of_interest')) {
                    description = component.long_name;
                    break;
                }
            }
            
            callback(description);
        } else {
            callback(`Location: ${lat.toFixed(6)}, ${lng.toFixed(6)}`);
        }
    });
}

/**
 * Validate map selection before form submission
 * @returns {boolean} True if valid location is selected
 */
function validateMapSelection() {
    const latitudeField = document.getElementById('latitude');
    const longitudeField = document.getElementById('longitude');
    
    if (!latitudeField || !longitudeField) {
        return true; // If no coordinate fields, validation passes
    }
    
    const hasCoordinates = latitudeField.value && longitudeField.value;
    
    if (!hasCoordinates) {
        if (window.SafeCampus?.showNotification) {
            window.SafeCampus.showNotification(
                'Please select a location on the map or enter a location description.',
                'warning'
            );
        }
        
        // Scroll to map
        document.getElementById('map')?.scrollIntoView({ behavior: 'smooth' });
        return false;
    }
    
    return true;
}

// Event listeners for form integration
document.addEventListener('DOMContentLoaded', function() {
    // Add validation to report form if it exists
    const reportForm = document.getElementById('reportForm');
    if (reportForm) {
        reportForm.addEventListener('submit', function(event) {
            if (!validateMapSelection()) {
                event.preventDefault();
                event.stopPropagation();
            }
        });
    }
    
    // Add clear button functionality if it exists
    const clearMapBtn = document.getElementById('clearMapBtn');
    if (clearMapBtn) {
        clearMapBtn.addEventListener('click', clearMapSelection);
    }

    const useLocationBtn = document.getElementById('useLocationBtn');
    if (useLocationBtn) {
        useLocationBtn.addEventListener('click', useCurrentLocation);
    }

        // Fallback: initialize map when Google Maps has already loaded
    if (!map && window.google && window.google.maps) {
        initMap();
    }
});

// Expose functions globally for use in templates
window.MapFunctions = {
    initMap,
    initModalMap,
    clearMapSelection,
    useCurrentLocation,
    getLocationDescription,
    validateMapSelection,
    handleMapClick
};

// Handle map load errors
window.gm_authFailure = function() {
    if (window.SafeCampus?.showNotification) {
        window.SafeCampus.showNotification(
            'Google Maps failed to load. Please check your API configuration.',
            'error'
        );
    }
    
    // Hide map container and show alternative
    const mapContainer = document.getElementById('map');
    if (mapContainer) {
        mapContainer.innerHTML = `
            <div class="text-center p-4 bg-light">
                <i class="fas fa-map text-muted mb-2" style="font-size: 2rem;"></i>
                <p class="text-muted mb-0">Map unavailable. Please enter location manually.</p>
            </div>
        `;
    }
};
