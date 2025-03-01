import React from 'react';
import PropTypes from 'prop-types';
import { Link } from '@reach/router';
import { siteRoot, gettext } from '../../../utils/constants';

const propTypes = {
  currentItem: PropTypes.string.isRequired,
  groupID: PropTypes.string.isRequired,
  groupName: PropTypes.string.isRequired,
};

class Nav extends React.Component {

  constructor(props) {
    super(props);
    this.navItems = [
      {name: 'tables', urlPart: 'groups/' + this.props.groupID + '/dtables', text: gettext('Tables')},
      {name: 'members', urlPart: 'groups/' + this.props.groupID + '/members', text: gettext('Members')},
      {name: 'storages', urlPart: 'groups/' + this.props.groupID + '/storages', text: gettext('Storage')}
    ];
  }

  render() {
    const { groupName, currentItem } = this.props;
    return (
      <div>
        <div className="cur-view-path">
          <h3 className="sf-heading"><Link to={`${siteRoot}sys/groups/`}>{gettext('Groups')}</Link> / {groupName}</h3>
        </div>
        <ul className="nav border-bottom mx-4">
          {this.navItems.map((item, index) => {
            return (
              <li className="nav-item mr-2" key={index}>
                <Link to={`${siteRoot}sys/${item.urlPart}/`} className={`nav-link ${currentItem === item.name ? ' active' : ''}`}>{item.text}</Link>
              </li>
            );
          })}
        </ul>
      </div>
    );
  }
}

Nav.propTypes = propTypes;

export default Nav;
