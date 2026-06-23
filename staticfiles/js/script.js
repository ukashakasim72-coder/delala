document.addEventListener('DOMContentLoaded', function() {
    const passwordField = document.getElementById('id_password');
    const togglePassword = document.getElementById('togglePassword');

    if (passwordField && togglePassword) {
        togglePassword.addEventListener('click', function() {
            // Toggle the type attribute
            const type = passwordField.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordField.setAttribute('type', type);

            // Toggle the eye icon (simple text for now)
            if (type === 'password') {
                togglePassword.innerHTML = '👁'; // Eye icon
            } else {
                togglePassword.innerHTML = '🕶'; // Eye-slash icon
            }
        });
    }

    const newPasswordField = document.getElementById('id_new_password1');
    const confirmPasswordField = document.getElementById('id_new_password2');
    const toggleNewPassword = document.getElementById('toggleNewPassword');
    const toggleConfirmPassword = document.getElementById('toggleConfirmPassword');

    if (newPasswordField && toggleNewPassword) {
        toggleNewPassword.addEventListener('click', function() {
            const type = newPasswordField.getAttribute('type') === 'password' ? 'text' : 'password';
            newPasswordField.setAttribute('type', type);
            if (type === 'password') {
                toggleNewPassword.innerHTML = '👁';
            } else {
                toggleNewPassword.innerHTML = '🕶';
            }
        });
    }

    if (confirmPasswordField && toggleConfirmPassword) {
        toggleConfirmPassword.addEventListener('click', function() {
            const type = confirmPasswordField.getAttribute('type') === 'password' ? 'text' : 'password';
            confirmPasswordField.setAttribute('type', type);
            if (type === 'password') {
                toggleConfirmPassword.innerHTML = '👁';
            } else {
                toggleConfirmPassword.innerHTML = '🕶';
            }
        });
    }
});







