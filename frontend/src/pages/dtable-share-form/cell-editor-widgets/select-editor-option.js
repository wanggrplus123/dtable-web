import React from 'react';
import PropTypes from 'prop-types';

const propTypes = {
  option: PropTypes.object.isRequired,
  isShowRemoveIcon: PropTypes.bool,
  onDeleteSelectOption: PropTypes.func,
};

/**
 * option : {
 *   id: '',
 *   name: '',
 *   color: '',
 * }
 */

class SelectEditorOption extends React.Component {

  static defaultProps = {
    isShowRemoveIcon: false,
  }

  onDeleteOption = (event) => {
    event.nativeEvent.stopImmediatePropagation();
    event.stopPropagation();
    this.props.onDeleteSelectOption(this.props.option);
  }

  getContainerStyle = () => {
    let option = this.props.option;
    return {
      display: 'inline-flex',
      marginRight: '10px',
      padding: '0px 10px',
      height: '20px',
      textAlign: 'center',
      borderRadius: '10px',
      fontSize: '13px',
      backgroundColor: option.color,
    };
  }

  getOptionStyle = (option) => {
    const textColor = option.textColor || null;
    return {
      flex: 1,
      display: 'flex',
      alignContent: 'center',
      margin: '0 4px 0 2px',
      color: textColor,
    };
  }

  getOperationStyle = (option) => {
    const textColor = option.textColor || null;
    return {
      height: '20px',
      width: '16px',
      cursor: 'pointer',
      color: textColor === '#FFFFFF' ? '#FFFFFF' : '#909090',
      transform: 'scale(.8)',
    };
  }

  render() {
    let { option, isShowRemoveIcon } = this.props;
    let containerStyle = this.getContainerStyle();
    let optionStyle = this.getOptionStyle(option);
    let operationStyle = this.getOperationStyle(option);

    return (
      <div className="select-option-item" style={containerStyle}>
        <div className="option-info" style={optionStyle}>
          <div className="option-name">{option.name}</div>
        </div>
        {isShowRemoveIcon && (
          <div className="option-remove" style={operationStyle} onClick={this.onDeleteOption}>
            <i className="dtable-font dtable-icon-fork-number" style={{fontSize: '12px', lineHeight: '20px'}}></i>
          </div>
        )}
      </div>
    );
  }
}

SelectEditorOption.propTypes = propTypes;

export default SelectEditorOption;
