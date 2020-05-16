import datetime
import dto.UserDTO
from Dao.userDAO import UserDAO, verify_if_email_already_exists, verify_if_username_already_exists
from Utils import UserUtils as UserConverter, UserUtils, SecurityUtils
from Enums import UserEnums, ErrorEnums, AdminPermissionEnums
from Utils import SecurityUtils as UserSecurity
import Utils.TimeUtils as TimeUtils
from Dao.sessionHistoryDAO import SessionHistoryDAO
from .sessionService import SessionService


def confirm_if_username_or_email_exists_already_during_registration(user_email, user_name) -> dict:
    user_instance = UserDAO.get_active_inactive_single_user_by_email(user_email)
    user_email_already_exists_error = "Another user with the same email already exists."
    username_already_exists_error = "Another user with the same username already exists."
    if user_instance:
        return {'result': True, 'value': user_email_already_exists_error}
    else:
        username_instance = UserDAO.get_user_by_username(user_name)
        if username_instance:
            return {'result': True, 'value': username_already_exists_error}


def verify_id_email_for_email_update(uid, email):
    user = UserDAO.get_user_by_id(uid)
    if not user:
        return {'result': False, 'error': 'No user found with id {}.'.format(uid)}
    if isinstance(user, dict) and 'error' in user.keys():
        return user
    if user and user.email != email:
        return {'result': False, 'error': 'Mismatch in id and oldEmail. Please correct the pair and retry again.'}
    return True


def get_all_users() -> list:
    users_from_persistence = UserDAO.get_all_active_users()
    aggregated_result = []
    for user in users_from_persistence:
        aggregated_result.append(dto.UserDTO.user_dto(user))
    return aggregated_result


def confirm_if_user_name_already_exists(username):
    user_instance = UserDAO.get_user_by_username(username)
    if user_instance.username == username:
        return True
    return False


def get_existing_user_by_username(username):
    user = UserDAO.get_user_by_username(username)
    return dto.UserDTO.user_dto(user)


def get_existing_user_by_email(email):
    user = UserDAO.get_active_inactive_single_user_by_email(email)
    if not user:
        return {'error': 'No user found for email {}.'.format(email)}
    return dto.UserDTO.user_dto(user)


def get_active_user_by_email(email):
    user = UserDAO.get_active_user_by_email(email)
    return dto.UserDTO.user_dto(user)


def create_update_user(user_id, user, is_user_id_provided: bool):
    phone_length_is_valid = is_phone_vaild(user.setdefault('phone_number', None))
    if not phone_length_is_valid:
        return ErrorEnums.INVALID_PHONE_LENGTH_ERROR.value
    if not UserUtils.validate_min_length(user.get('password'), UserEnums.MIN_PASSWORD_LENGTH.value):
        return ErrorEnums.INVALID_PASSWORD_LENGTH_ERROR.value
    user['password'] = UserSecurity.encrypt_pass(user.get('password'))
    user['date_of_birth'] = TimeUtils.convert_time(user.get('date_of_birth'))
    if not is_user_id_provided:
        created_user = UserDAO.create_user(user)
        if isinstance(created_user, str):
            return {'error': created_user}
        return UserConverter.convert_user_dto_to_public_response_dto(created_user)
    updated_user = UserDAO.update_user_generic_data(user_id, user)
    return updated_user


def get_existing_user_by_id(identity) -> dict:
    user = UserDAO.get_user_by_id(identity)
    if isinstance(user, dict):
        return user
    return dto.UserDTO.user_dto(user)


def update_user_email(user, old_em, new_em):
    is_length_invalid = UserUtils.verify_email_length(old_em, new_em)
    if is_length_invalid:
        return is_length_invalid
    u = get_existing_user_by_id(user['id'])
    if 'error' in u.keys():
        return [u, 500]
    if u['email'] != old_em:
        return [{'error': '{} does not match your current email address. Please check and try again.'.format(old_em)}, 404]
    elif old_em == new_em:
        return [{'error': 'Email is already up to date for the user.'}, 200]
    email_exists_already = verify_if_email_already_exists(new_em)
    if email_exists_already:
        return [{'error': 'Cannot update email as the user with email id - {} already exists.'.format(new_em)}, 409]
    updated_user = UserDAO.update_email(user['id'], new_em)
    return updated_user


def activate_deactivate_user(
        curr_user: dict, email: str, is_admin_action: bool, action) -> list:
    print(
        'Log: activation deactivation request received at {} for'
        ' \nuser: {},\nemail: {},\nadmin_action: {},\npermission: {}]'.format(
            str(datetime.datetime.now()), curr_user, email, is_admin_action, action
        ))
    email_length_invalid = UserUtils.verify_email_length(email, email)
    if email_length_invalid:
        return email_length_invalid
    elif curr_user.get('email') != email and not is_admin_action:
        return [{'error': 'Please provide your own valid email id address.'}, 404]
    UserDAO.activate_deactivate_user(curr_user.get('email'), email, is_admin_action, action)
    if action == AdminPermissionEnums.DEACTIVATE.name:
        deleted_user = dto.UserDTO.user_dto(UserDAO.get_active_inactive_single_user_by_email(email))
        if deleted_user and not deleted_user.get('is_active'):
            # # Active tokens for current user should be revoked as soon as the user marks himself as inactive.
            user_session_history = SessionHistoryDAO()
            session_bucket = user_session_history.get_active_sessions_for_user(deleted_user)
            if session_bucket:
                session_service = SessionService()
                session_service.revoke_session_token(session_bucket[0].get('access_token_jti'))
            return [{'response': 'User successfully deleted.'}, 200]
        return [{'error': 'No user with email {} found.'.format(email)}, 400]
    elif action == AdminPermissionEnums.ACTIVATE.name:
        activated_user = dto.UserDTO.user_dto(UserDAO.get_active_inactive_single_user_by_email(email))
        if activated_user and activated_user.get('is_active'):
            return [{'response': 'User successfully restored.'}, 200]
        return [{'error': 'No user with email {} found .'.format(email)}, 400]
    print("Some error encountered, {}.".format(str(datetime.datetime.now())))
    return [{'error': 'There was some error, please contact developer.'}, 500]


def update_password(user, old_password, new_password):
    if not UserUtils.validate_min_length(
            old_password, UserEnums.MIN_PASSWORD_LENGTH.value
    ) or not UserUtils.validate_min_length(new_password, UserEnums.MIN_PASSWORD_LENGTH.value):
        return [
            {
                'error': ErrorEnums.INVALID_PASSWORD_LENGTH_ERROR.value
            }, 404
        ]
    persisted_p, requested_p = SecurityUtils.encrypt_pass(old_password), SecurityUtils.encrypt_pass(new_password)
    updated_user = UserDAO.update_password(user.get('id'), persisted_p, requested_p)
    return updated_user


def update_user_name(user: dict, old_username: str, new_username: str):
    is_length_verified = UserUtils.verify_username_length(old_username, new_username)
    if is_length_verified:
        return is_length_verified
    user = get_existing_user_by_id(user['id'])
    if 'error' in user.keys():
        return [user, 500]
    elif old_username != user['username']:
        return [
            {
                'Error': '{} does not match the current username. Please correct your username and retry again.'
                         .format(old_username)
            }, 404
        ]
    elif old_username == new_username:
        return [{'error': 'Username is already up to date for the user.'}, 200]
    if verify_if_username_already_exists(new_username):
        return [{'error': 'User with username - {} already exists.'.format(new_username)}, 409]
    response = UserDAO.update_username(user['id'], new_username)
    return response


def is_phone_vaild(phone_num):
    if not phone_num:
        return True
    length = len(str(phone_num))
    if length < UserEnums.MIN_PHONE_NUMBER_LENGTH.value or length > UserEnums.MAX_PHONE_NUMBER_LENGTH.value:
        return False
    return True


def admin_access(user_email: str, permission_type: str) -> list:
    user = UserDAO.get_active_inactive_single_user_by_email(user_email)
    if not user.is_active:
        return [{'error': 'Cannot grant access as the user is inactive. Please activate the user profile first.'}, 400]
    access_type = AdminPermissionEnums.__dict__.get(permission_type.upper())
    UserDAO.admin_access(user_email, access_type.value)
    verify_user_access = UserDAO.get_active_user_by_email(user_email).is_admin
    if verify_user_access is True:
        return [{'response': 'User granted admin privileges.'}, 200]
    elif verify_user_access is False:
        return [{'response': 'User revoked from admin privileges.'}, 200]
    return [{'error': 'There was some error.'}, 500]
