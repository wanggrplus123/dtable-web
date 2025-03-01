import React, { Component, Fragment } from 'react';
import PropTypes from 'prop-types';
import { Link } from '@reach/router';
import moment from 'moment';
import { Utils } from '../../../utils/utils';
import { dtableWebAPI } from '../../../utils/dtable-web-api';
import { siteRoot, loginUrl, gettext } from '../../../utils/constants';
import toaster from '../../../components/toast';
import EmptyTip from '../../../components/empty-tip';
import Loading from '../../../components/loading';
import CommonOperationConfirmationDialog from '../../../components/dialog/common-operation-confirmation-dialog';
import MainPanelTopbar from '../main-panel-topbar';
import Nav from './user-nav';
import OpMenu from './user-op-menu';

const contentPropTypes = {
  loading: PropTypes.bool.isRequired,
  errorMsg: PropTypes.string,
  items: PropTypes.array,
  deleteItem: PropTypes.func.isRequired
};

class Content extends Component {

  constructor(props) {
    super(props);
    this.state = {
      isItemFreezed: false
    };
  }

  onFreezedItem = () => {
    this.setState({isItemFreezed: true});
  }

  onUnfreezedItem = () => {
    this.setState({isItemFreezed: false});
  }

  render() {
    const { loading, errorMsg, items } = this.props;
    if (loading) {
      return <Loading />;
    } else if (errorMsg) {
      return <p className="error text-center mt-4">{errorMsg}</p>;
    } else {
      const emptyTip = (
        <EmptyTip>
          <h2>{gettext('No groups')}</h2>
        </EmptyTip>
      );
      const table = (
        <Fragment>
          <table>
            <thead>
              <tr>
                <th width="35%">{gettext('Name')}</th>
                <th width="30%">{gettext('Role')}</th>
                <th width="30%">{gettext('Created At')}</th>
                <th width="5%">{/* Operations */}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, index) => {
                return (<Item
                  key={index}
                  item={item}
                  isItemFreezed={this.state.isItemFreezed}
                  onFreezedItem={this.onFreezedItem}
                  onUnfreezedItem={this.onUnfreezedItem}
                  deleteItem={this.props.deleteItem}
                />);
              })}
            </tbody>
          </table>
        </Fragment>
      );
      return items.length ? table : emptyTip; 
    }
  }
}

Content.propTypes = contentPropTypes;

const itemPropTypes = {
  item: PropTypes.object,
  isItemFreezed: PropTypes.bool.isRequired,
  onFreezedItem: PropTypes.func.isRequired,
  onUnfreezedItem: PropTypes.func.isRequired,
  deleteItem: PropTypes.func.isRequired,
};

class Item extends Component {

  constructor(props) {
    super(props);
    this.state = {
      isOpIconShown: false,
      highlight: false,
      isDeleteDialogOpen: false
    };
  }

  handleMouseEnter = () => {
    if (!this.props.isItemFreezed) {
      this.setState({
        isOpIconShown: true,
        highlight: true
      });
    }
  }

  handleMouseLeave = () => {
    if (!this.props.isItemFreezed) {
      this.setState({
        isOpIconShown: false,
        highlight: false
      });
    }
  }

  onUnfreezedItem = () => {
    this.setState({
      highlight: false,
      isOpIconShow: false
    });
    this.props.onUnfreezedItem();
  }

  toggleDeleteDialog = () => {
    this.setState({isDeleteDialogOpen: !this.state.isDeleteDialogOpen});
  }

  deleteItem = () => {
    this.props.deleteItem(this.props.item.id);
  }

  translateOperations = (item) => {
    let translateResult = ''; 
    switch (item) {
      case 'Delete':
        translateResult = gettext('Delete');
        break;
      default:
        break;
    }

    return translateResult;
  }

  onMenuItemClick = (operation) => {
    switch(operation) {
      case 'Delete':
        this.toggleDeleteDialog();
        break;
      default:
        break;
    }
  }

  getRoleText = () => {
    let roleText;
    const { item } = this.props;
    switch(item.role) {
      case 'Owner':
        roleText = gettext('Owner');
        break;
      case 'Admin':
        roleText = gettext('Admin');
        break;
      case 'Member':
        roleText = gettext('Member');
        break;
      default:
        break;
    }
    return roleText;
  }

  render() {
    const { item } = this.props;
    const { isOpIconShown, isDeleteDialogOpen } = this.state;

    const itemName = '<span class="op-target">' + Utils.HTMLescape(item.name) + '</span>';
    const deleteDialogMsg = gettext('Are you sure you want to delete {placeholder} ?').replace('{placeholder}', itemName);

    const url = item.parent_group_id === 0 ? 
      `${siteRoot}sys/groups/${item.id}/members/` :
      `${siteRoot}sys/departments/${item.id}/`;

    return (
      <Fragment>
        <tr className={this.state.highlight ? 'tr-highlight' : ''} onMouseEnter={this.handleMouseEnter} onMouseLeave={this.handleMouseLeave}>
          <td><Link to={url}>{item.name}</Link></td>
          <td>{this.getRoleText()}</td>
          <td>{moment(item.created_at).format('YYYY-MM-DD HH:mm')}</td>
          <td>
            {(isOpIconShown && item.parent_group_id === 0) &&
            <OpMenu
              operations={['Delete']}
              translateOperations={this.translateOperations}
              onMenuItemClick={this.onMenuItemClick}
              onFreezedItem={this.props.onFreezedItem}
              onUnfreezedItem={this.onUnfreezedItem}
            />
            }   
          </td>
        </tr>
        {isDeleteDialogOpen &&
          <CommonOperationConfirmationDialog
            title={gettext('Delete Group')}
            message={deleteDialogMsg}
            executeOperation={this.deleteItem}
            confirmBtnText={gettext('Delete')}
            toggleDialog={this.toggleDeleteDialog}
          />
        }
      </Fragment>
    );
  }
}

Item.propTypes = itemPropTypes;

const groupPropTypes = {
  email: PropTypes.string,
  onCloseSidePanel: PropTypes.func
};

class Groups extends Component {

  constructor(props) {
    super(props);
    this.state = {
      loading: true,
      errorMsg: '',
      userInfo: {},
      items: []
    };
  }

  componentDidMount () {
    dtableWebAPI.sysAdminGetUser(this.props.email).then((res) => {
      this.setState({
        userInfo: res.data
      }); 
    });
    dtableWebAPI.sysAdminListGroupsJoinedByUser(this.props.email).then(res => {
      this.setState({
        loading: false,
        items: res.data.group_list
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

  deleteItem = (groupID) => {
    dtableWebAPI.sysAdminDismissGroupByID(groupID).then(res => {
      let items = this.state.items.filter(item => {
        return item.id !== groupID;
      });
      this.setState({items: items});
      toaster.success(gettext('Successfully deleted 1 item.'));
    }).catch((error) => {
      let errMessage = Utils.getErrorMsg(error);
      toaster.danger(errMessage);
    });
  }

  render() {
    return (
      <Fragment>
        <MainPanelTopbar onCloseSidePanel={this.props.onCloseSidePanel} />
        <div className="main-panel-center flex-row">
          <div className="cur-view-container">
            <Nav currentItem="groups" email={this.props.email} userName={this.state.userInfo.name} />
            <div className="cur-view-content">
              <Content
                loading={this.state.loading}
                errorMsg={this.state.errorMsg}
                items={this.state.items}
                deleteItem={this.deleteItem}
              />
            </div>
          </div>
        </div>
      </Fragment>
    );
  }
}

Groups.propTypes = groupPropTypes;

export default Groups;
