function togglePasswordVisibility(passwordFieldId, toggleButtonId) {
    const passwordInput = document.getElementById(passwordFieldId);
    const toggleBtn = document.getElementById(toggleButtonId);

    if (passwordInput && toggleBtn) {
        toggleBtn.addEventListener('click', function () {
            const type = passwordInput.type === 'password' ? 'text' : 'password';
            passwordInput.type = type;

            // Optional: toggle a class for styling the icon
            toggleBtn.classList.toggle('showing');
        });
    }
}

// Call the function when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    togglePasswordVisibility('password', 'passwordToggle');
});
