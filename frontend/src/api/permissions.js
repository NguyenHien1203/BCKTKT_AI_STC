import { authIdentityClient } from "./orgUnits";

export async function getPermissionContext(userId) {
  const { data } = await authIdentityClient.get(`/users/${userId}/permission-context`);
  return data;
}

export async function assignRoleToUser(userId, roleCode) {
  const { data } = await authIdentityClient.patch(
    `/users/${userId}/permission-context/role`,
    { role_code: roleCode }
  );
  return data;
}

export async function configureUserDomains(userId, permittedDomains, permittedUnitId) {
  const { data } = await authIdentityClient.patch(
    `/users/${userId}/permission-context/domains`,
    { permitted_domains: permittedDomains, permitted_unit_id: permittedUnitId }
  );
  return data;
}

export async function configureUserSensitivity(userId, sensitivityLevel) {
  const { data } = await authIdentityClient.patch(
    `/users/${userId}/permission-context/sensitivity`,
    { sensitivity_level: sensitivityLevel }
  );
  return data;
}