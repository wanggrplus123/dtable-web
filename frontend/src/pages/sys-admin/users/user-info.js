import React, { Component, Fragment } from 'react';
import PropTypes from 'prop-types';
import { FormGroup, Label, Input, Button } from 'reactstrap';
import { Utils } from '../../../utils/utils';
import { dtableWebAPI } from '../../../utils/dtable-web-api';
import { loginUrl, gettext } from '../../../utils/constants';
import toaster from '../../../components/toast';
import Loading from '../../../components/loading';
import SysAdminSetQuotaDialog from '../../../components/dialog/sysadmin-dialog/set-quota';
import SysAdminUpdateUserDialog from '../../../components/dialog/sysadmin-dialog/update-user';
import MainPanelTopbar from '../main-panel-topbar';
import Nav from './user-nav';

const { twoFactorAuthEnabled } = window.sysadmin.pageOptions;

const contentPropTypes = {
  loading: PropTypes.bool.isRequired,
  errorMsg: PropTypes.string,
  userInfo: PropTypes.object,
  updateUser: PropTypes.func.isRequired,
  disable2FA: PropTypes.func.isRequired,
  toggleForce2fa: PropTypes.func.isRequired,
};

class Content extends Component {

  constructor(props) {
    super(props);
    this.state = {
      currentKey: '',
      dialogTitle: '',
      isSetQuotaDialogOpen: false,
      isUpdateUserDialogOpen: false
    };
  }

  toggleSetQuotaDialog = () => {
    this.setState({isSetQuotaDialogOpen: !this.state.isSetQuotaDialogOpen});
  }

  updateQuota = (value) => {
    this.props.updateUser('quota_total', value);
  }

  toggleDialog = (key, dialogTitle) => {
    this.setState({
      currentKey: key,
      dialogTitle: dialogTitle,
      isUpdateUserDialogOpen: !this.state.isUpdateUserDialogOpen
    });
  }

  toggleSetNameDialog = () => {
    this.toggleDialog('name', gettext('Set Name'));
  }

  toggleSetUserLoginIDDialog = () => {
    this.toggleDialog('login_id', gettext('Set Login ID'));
  }

 toggleSetUserComtactEmailDialog = () => {
   this.toggleDialog('contact_email', gettext('Set Contact Email'));
 }

  updateValue = (value) => {
    this.props.updateUser(this.state.currentKey, value);
  }

  toggleUpdateUserDialog = () => {
    this.toggleDialog('', '');
  }

  showEditIcon = (action) => {
    return (
      <span
        title={gettext('Edit')}
        className="dtable-font dtable-icon-rename attr-action-icon"
        onClick={action}>
      </span>
    );
  }

  render() {
    const { loading, errorMsg } = this.props;
    if (loading) {
      return <Loading />;
    } else if (errorMsg) {
      return <p className="error text-center mt-4">{errorMsg}</p>;
    } else {
      const user = this.props.userInfo;
      const { 
        currentKey, dialogTitle,
        isSetQuotaDialogOpen, isUpdateUserDialogOpen
      } = this.state;
      return (
        <Fragment>
          <dl className="m-0">
            <dt className="info-item-heading">{gettext('Avatar')}</dt>
            <dd className="info-item-content">
              <img src={user.avatar_url} alt={user.name} width="80" className="rounded"  />
            </dd>

            <dt className="info-item-heading">{'ID'}</dt>
            <dd className="info-item-content">{user.email}</dd>

            {user.org_name &&
              <Fragment>
                <dt className="info-item-heading">{gettext('Organization')}</dt>
                <dd className="info-item-content">{user.org_name}</dd>
              </Fragment>
            }

            <dt className="info-item-heading">{gettext('Name')}</dt>
            <dd className="info-item-content">
              {user.name || '--'}
              {this.showEditIcon(this.toggleSetNameDialog)}
            </dd>

            <dt className="info-item-heading">{gettext('Login ID')}</dt>
            <dd className="info-item-content">
              {user.login_id || '--'}
              {this.showEditIcon(this.toggleSetUserLoginIDDialog)}
            </dd>

            <dt className="info-item-heading">{gettext('Contact Email')}</dt>
            <dd className="info-item-content">
              {user.contact_email || '--'}
              {this.showEditIcon(this.toggleSetUserComtactEmailDialog)}
            </dd>

            <dt className="info-item-heading">{gettext('Storage Usage')}</dt>
            <dd className="info-item-content">{Utils.bytesToSize(user.storage_usage)}</dd>

            {twoFactorAuthEnabled &&
              <Fragment>
                <dt className="info-item-heading">{gettext('Two-Factor Authentication')}</dt>
                <dd className="info-item-content">
                  {user.has_default_device ?
                    <FormGroup>
                      <p className="mb-1">{gettext('Status: enabled')}</p>
                      <Button onClick={this.props.disable2FA}>{gettext('Disable Two-Factor Authentication')}</Button>
                    </FormGroup> :
                    <FormGroup>
                      <Button disabled={true}>{gettext('Disable Two-Factor Authentication')}</Button>
                    </FormGroup>
                  }
                  <FormGroup check>
                    <Label check>
                      <Input type="checkbox" checked={user.is_force_2fa} onChange={this.props.toggleForce2fa} />
                      <span>{gettext('Force Two-Factor Authentication')}</span>
                    </Label>
                  </FormGroup>
                </dd>
              </Fragment>
            }
          </dl>
          {isSetQuotaDialogOpen &&
          <SysAdminSetQuotaDialog
            updateQuota={this.updateQuota}
            toggle={this.toggleSetQuotaDialog}
          />
          }
          {isUpdateUserDialogOpen &&
          <SysAdminUpdateUserDialog
            dialogTitle={dialogTitle}
            value={user[currentKey]}
            updateValue={this.updateValue}
            toggleDialog={this.toggleUpdateUserDialog}
          />
          }
        </Fragment>
      );
    }
  }
}

Content.propTypes = contentPropTypes;

const userPropTypes = {
  email: PropTypes.string,
  onCloseSidePanel: PropTypes.func
};

class User extends Component {

  constructor(props) {
    super(props);
    this.state = {
      loading: true,
      errorMsg: '',
      userInfo: {}
    };
  }

  componentDidMount () {
    // avatar size: 160
    dtableWebAPI.sysAdminGetUser(this.props.email, 160).then((res) => {
      this.setState({
        loading: false,
        userInfo: res.data
      });
    }).catch((error) => {
      if (error.response) {
        if (error.response.status === 403) {
          this.setState({
            loading: false,
            errorMsg: gettext('Permission denied')
          }); 
          location.href = `${loginUrl}?next=${encodeURIComponent(location.href)}`;
        } else {
          this.setState({
            loading: false,
            errorMsg: gettext('Error')
          }); 
        }   
      } else {
        this.setState({
          loading: false,
          errorMsg: gettext('Please check the network.')
        });
      }
    });
  }

  updateUser = (key, value) => {
    const email = this.state.userInfo.email;
    dtableWebAPI.sysAdminUpdateUser(email, key, value).then(res => {
      let userInfo = this.state.userInfo;
      userInfo[key]= res.data[key];
      this.setState({
        userInfo: userInfo 
      });
      toaster.success(gettext('Edit succeeded'));
    }).catch((error) => {
      let errMessage = Utils.getErrorMsg(error);
      toaster.danger(errMessage);
    }); 
  }

  disable2FA = () => {
    const email = this.state.userInfo.email;
    dtableWebAPI.sysAdminDeleteTwoFactorAuth(email).then(res => {
      let userInfo = this.state.userInfo;
      userInfo.has_default_device = false;
      this.setState({
        userInfo: userInfo 
      });
    }).catch((error) => {
      let errMessage = Utils.getErrorMsg(error);
      toaster.danger(errMessage);
    });
  }

  toggleForce2fa = (e) => {
    const email = this.state.userInfo.email;
    const checked = e.target.checked;
    dtableWebAPI.sysAdminSetForceTwoFactorAuth(email, checked).then(res => {
      let userInfo = this.state.userInfo;
      userInfo.is_force_2fa = checked;
      this.setState({
        userInfo: userInfo 
      });
    }).catch((error) => {
      let errMessage = Utils.getErrorMsg(error);
      toaster.danger(errMessage);
    });
  }

  render() {
    const { userInfo } = this.state;
    return (
      <Fragment>
        <MainPanelTopbar onCloseSidePanel={this.props.onCloseSidePanel} />
        <div className="main-panel-center flex-row">
          <div className="cur-view-container">
            <Nav currentItem="info" email={this.props.email} userName={userInfo.name} />
            <div className="cur-view-content">
              <Content
                loading={this.state.loading}
                errorMsg={this.state.errorMsg}
                userInfo={this.state.userInfo}
                updateUser={this.updateUser}
                disable2FA={this.disable2FA}
                toggleForce2fa={this.toggleForce2fa}
              />
            </div>
          </div>
        </div>
      </Fragment>
    );
  }
}

User.propTypes = userPropTypes;

export default User;
